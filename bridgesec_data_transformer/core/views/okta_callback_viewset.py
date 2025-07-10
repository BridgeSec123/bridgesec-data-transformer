import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.utils.jwt_utils import generate_jwt_token
from core.models.user import User
from bson import ObjectId
from jose import jwt

class OktaCallbackView(APIView):
    def get(self, request):
        code = request.GET.get("code")
    
        token_url = f"{settings.OKTA_ISSUER}/v1/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OKTA_REDIRECT_URI,
            "client_id": settings.OKTA_CLIENT_ID,
            "client_secret": settings.OKTA_SECRET_KEY,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_resp = requests.post(token_url, data=data, headers=headers)
        token_data = token_resp.json()
        id_token = token_data.get("id_token")
        access_token = token_data.get("access_token")

        if not id_token or not access_token:
            return Response({"error": "Token not received"}, status=400)
        
        # Decode token
        jwks_url = f"{settings.OKTA_ISSUER}/v1/keys"
        jwks = requests.get(jwks_url).json()
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header["kid"]

        key = next(k for k in jwks["keys"] if k["kid"] == kid)

        payload = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=settings.OKTA_CLIENT_ID,
            issuer=settings.OKTA_ISSUER,
            access_token=access_token 
        )

        email = payload.get("email") or payload.get("sub")
        username = email  # or however you want to define username

        if not email:
            return Response({"error": "Email is required from Okta"}, status=400)

        user = User.objects(email=email).first()
        if not user:
            user = User(email=email, username=username, role="admin")
            user.save()

        # Generate custom access token
        jwt_token = generate_jwt_token(user)

        user_data = {
            "id": str(user.id),     # This is likely an ObjectId
            "username": user.username,
            "role": user.role,
          }
        return Response({"access_token": jwt_token, "user":user_data}, status=status.HTTP_200_OK)