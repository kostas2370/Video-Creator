from django.core.exceptions import ValidationError
from rest_framework_simplejwt import authentication as jwt_authentication
from rest_framework import exceptions as rest_exceptions


class CustomAuthentication(jwt_authentication.JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        candidates = [
            request.COOKIES.get("access_token") or None,
            self.get_raw_token(header) if header is not None else None,
        ]

        for raw_token in candidates:
            if raw_token is None:
                continue

            try:
                validated_token = self.get_validated_token(raw_token)
            except rest_exceptions.AuthenticationFailed:
                continue

            try:
                return self.get_user(validated_token), validated_token
            except ValidationError as exc:
                raise rest_exceptions.AuthenticationFailed("Invalid user identifier.") from exc

        return None
