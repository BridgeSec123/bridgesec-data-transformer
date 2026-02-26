import logging
import time

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

PENDING_JWT_TTL_SECONDS = 60


class TokenRetrievalView(APIView):
    def get(self, request):
        session = request.session
        pending_jwt = session.get("pending_jwt")
        issued_at = session.get("pending_jwt_issued_at")

        if not pending_jwt or issued_at is None:
            logger.warning(
                "Token retrieval failed: no pending JWT in session",
                extra={'component': 'auth', 'action': 'token_retrieval'}
            )
            return Response(
                {"error": "No pending authentication found. Please login again."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if time.time() - issued_at > PENDING_JWT_TTL_SECONDS:
            session.pop("pending_jwt", None)
            session.pop("pending_jwt_issued_at", None)
            session.save()
            logger.warning(
                "Token retrieval failed: pending JWT expired",
                extra={'component': 'auth', 'action': 'token_retrieval'}
            )
            return Response(
                {"error": "Authentication session expired. Please login again."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # One-time use: delete from session immediately after reading
        session.pop("pending_jwt", None)
        session.pop("pending_jwt_issued_at", None)
        session.save()

        logger.info(
            "Token retrieved successfully",
            extra={
                'component': 'auth',
                'action': 'token_retrieval',
                'user': session.get("email"),
            }
        )

        return Response({
            "access_token": pending_jwt,
            "token_type": "Bearer",
            "expires_in": 86400,
            "user": {
                "email": session.get("email"),
                "username": session.get("username"),
                "role": session.get("role"),
            }
        }, status=status.HTTP_200_OK)
