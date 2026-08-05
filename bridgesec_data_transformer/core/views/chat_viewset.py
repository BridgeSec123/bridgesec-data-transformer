import json
import logging

import anthropic
import requests
from core.authentication import CustomJWTAuthentication
from core.permissions.decorators import require_permission
from core.utils.activity_logger import ActivityLogger
from core.utils.chat_tools import execute_tool, get_tools_for_user
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

# Lazy so a Groq-only deployment doesn't require an Anthropic key at import time.
_anthropic_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client

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

    @require_permission("view_chat")
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

        # Provider + model are selectable per request; fall back to configured defaults.
        provider = (request.data.get("provider") or settings.CHAT_PROVIDER).lower()
        model = request.data.get("model")

        try:
            if provider == "groq":
                reply = self._run_groq_loop(
                    messages, tools, user_token, request.user,
                    model or settings.GROQ_MODEL,
                )
            else:
                reply = self._run_anthropic_loop(
                    messages, tools, user_token, request.user,
                    model or settings.ANTHROPIC_MODEL,
                )
            return Response({"reply": reply, "role": "assistant", "provider": provider})

        except anthropic.AuthenticationError:
            logger.error("Anthropic API key is invalid or missing")
            return Response(
                {"error": "AI service authentication failed. Contact your administrator."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except requests.RequestException as e:
            logger.error(f"Groq request failed: {e}")
            return Response(
                {"error": "AI service unavailable. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception(f"Chat error for user {request.user}: {e}")
            return Response(
                {"error": "An unexpected error occurred. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _execute_and_log(self, name: str, tool_input: dict, user_token: str, user) -> dict:
        """Run a tool call, write the audit trail, and normalize errors to a dict.
        Shared by both provider loops."""
        logger.info(f"Tool call: user={user} tool={name} input_keys={list(tool_input.keys())}")

        # Activity log (audit trail) — only when tenant_id is available; never block the response.
        try:
            tenant_id = getattr(user, "tenant_id", None)
            if tenant_id:
                ActivityLogger.log(
                    tenant_id=tenant_id,
                    user_email=getattr(user, "email", str(user)),
                    action=f"chat_tool:{name}",
                    details={"input_keys": list(tool_input.keys())},
                )
        except Exception:
            pass

        try:
            return execute_tool(name, tool_input, user_token)
        except Exception as e:
            logger.error(f"Tool '{name}' failed for user={user}: {e}")
            return {"error": str(e)}

    def _run_anthropic_loop(
        self, messages: list, tools: list, user_token: str, user, model: str
    ) -> str:
        """
        Anthropic agentic loop (native Messages API format):
          1. Send messages to Claude.
          2. If Claude wants tools → execute them, append results, repeat.
          3. If Claude gives a final text answer → return it.
        Max 10 iterations to prevent infinite loops.
        """
        max_iterations = 10

        for iteration in range(max_iterations):
            response = _get_anthropic().messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "",
                )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    result = self._execute_and_log(block.name, block.input, user_token, user)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

                messages.append({"role": "user", "content": tool_results})

            else:
                logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                return next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "Unexpected response from AI. Please try again.",
                )

        logger.warning(f"Agent loop hit max iterations ({max_iterations}) for user={user}")
        return "The request required too many steps to complete. Please try a more specific query."

    def _run_groq_loop(
        self, messages: list, tools: list, user_token: str, user, model: str
    ) -> str:
        """
        Groq agentic loop (OpenAI-compatible /chat/completions format).
        Wraps the Anthropic-format tool defs into OpenAI function schema inline.
        Max 10 iterations to prevent infinite loops.
        """
        oai_tools = [{"type": "function", "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }} for t in tools]
        convo = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        max_iterations = 10

        for iteration in range(max_iterations):
            resp = requests.post(
                f"{settings.GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={
                    "model": model,
                    "messages": convo,
                    "tools": oai_tools,
                    "tool_choice": "auto",
                    "max_tokens": 4096,
                },
                timeout=settings.CHAT_TIMEOUT,
            )
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]

            calls = msg.get("tool_calls")
            if not calls:
                return msg.get("content") or ""

            convo.append(msg)
            for call in calls:
                fn = call["function"]
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    args = json.loads(args)
                result = self._execute_and_log(fn["name"], args, user_token, user)
                convo.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                })

        logger.warning(f"Agent loop hit max iterations ({max_iterations}) for user={user}")
        return "The request required too many steps to complete. Please try a more specific query."
