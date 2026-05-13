import json
import logging

import anthropic
from core.authentication import CustomJWTAuthentication
from core.utils.activity_logger import ActivityLogger
from core.utils.chat_tools import execute_tool, get_tools_for_user
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an AI assistant for BridgeSec Data Transformer — an enterprise tool \
for managing Okta backups, restores, and configurations.

You help users:
- Browse and explore Okta snapshot databases
- Compare configurations between snapshots to detect drift
- Restore or modify Okta resources from historical snapshots
- Create new Okta entities
- Understand what changed in their Okta environment over time

Guidelines:
- Always confirm with the user before executing any write operation (restore, create, trigger_bulk_fetch).
- For deletions: always call plan_deletion first, show the full plan summary to the user, \
and wait for their explicit "yes" / "confirm" before calling confirm_deletion.
- If a user says "cancel" or "no" to a pending deletion, call cancel_deletion immediately.
- Keep responses concise and structured. Use markdown tables or bullet lists where helpful.
- If a tool returns an error, explain it in plain language and suggest next steps.
- Never expose raw JWT tokens, internal IDs, or sensitive fields in your responses."""


class ChatView(APIView):
    """
    POST /api/chat/

    Accepts a user message and optional conversation history.
    Runs an agentic loop: Claude decides which tools to call, results are fed back,
    until Claude produces a final text answer.

    All tool calls use the authenticated user's own Bearer token — never a service token.
    Data is automatically scoped to the user's tenant via Django's existing JWT middleware.

    Request body:
        {
            "message": "Show me all users from the latest snapshot",
            "history": [                          // optional — previous turns
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

    Response:
        {
            "reply": "Here are the users...",
            "role": "assistant"
        }
    """

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="AI Chat Assistant",
        operation_description=(
            "Send a natural language message to the BridgeSec AI assistant.\n\n"
            "The assistant can list snapshots, fetch entity data, compare snapshots, "
            "restore/create entities, and manage deletions — all scoped to the authenticated user's tenant.\n\n"
            "Pass `history` to maintain a multi-turn conversation."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["message"],
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The user's natural language query",
                    example="List all available snapshots",
                ),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "reply": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="AI assistant's response",
                    ),
                    "role": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="assistant",
                    ),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
            ),
            401: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
            ),
            503: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
            ),
        },
        security=[{"Bearer": []}],
        tags=["Chat"],
    )
    def post(self, request):
        user_message = request.data.get("message", "").strip()
        conversation_history = request.data.get("history", [])

        if not user_message:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract the user's own Bearer token from the incoming request.
        # This token is forwarded to every tool call — never replaced with a service token.
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        user_token = auth_header.replace("Bearer ", "").strip()

        if not user_token:
            return Response(
                {"error": "Authorization token missing"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Tools are filtered by the user's role (admin gets write tools, viewer gets read-only)
        tools = get_tools_for_user(request.user)

        messages = list(conversation_history) + [
            {"role": "user", "content": user_message}
        ]

        try:
            reply = self._run_agent_loop(messages, tools, user_token, request.user)
            return Response({"reply": reply, "role": "assistant"})

        except anthropic.AuthenticationError:
            logger.error("Anthropic API key is invalid or missing")
            return Response(
                {"error": "AI service authentication failed. Contact your administrator."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception(f"Chat error for user {request.user}: {e}")
            return Response(
                {"error": "An unexpected error occurred. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _run_agent_loop(
        self, messages: list, tools: list, user_token: str, user
    ) -> str:
        """
        Agentic loop:
          1. Send messages to Claude.
          2. If Claude wants to call tools → execute them, append results, repeat.
          3. If Claude gives a final text answer → return it.

        Max 10 iterations to prevent infinite loops.
        """
        max_iterations = 10

        for iteration in range(max_iterations):
            response = claude_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            # Claude produced a final text response
            if response.stop_reason == "end_turn":
                return next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "",
                )

            # Claude wants to call one or more tools
            if response.stop_reason == "tool_use":
                # Append Claude's response (including tool_use blocks) to history
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    logger.info(
                        f"Tool call: user={user} tool={block.name} "
                        f"input_keys={list(block.input.keys())}"
                    )

                    # Log to activity log (audit trail) — only when tenant_id is available
                    try:
                        tenant_id = getattr(user, "tenant_id", None)
                        if tenant_id:
                            ActivityLogger.log(
                                tenant_id=tenant_id,
                                user_email=getattr(user, "email", str(user)),
                                action=f"chat_tool:{block.name}",
                                details={"input_keys": list(block.input.keys())},
                            )
                    except Exception:
                        pass  # Never let logging block the response

                    try:
                        result = execute_tool(block.name, block.input, user_token)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                    except Exception as e:
                        logger.error(
                            f"Tool '{block.name}' failed for user={user}: {e}"
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True,
                        })

                # Feed tool results back — Claude will process and either answer or call more tools
                messages.append({"role": "user", "content": tool_results})

            else:
                # Unexpected stop reason — return whatever text is available
                logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                return next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "Unexpected response from AI. Please try again.",
                )

        logger.warning(f"Agent loop hit max iterations ({max_iterations}) for user={user}")
        return "The request required too many steps to complete. Please try a more specific query."
