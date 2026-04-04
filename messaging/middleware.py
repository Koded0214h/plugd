from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.db import close_old_connections
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        close_old_connections()
        
        # Get the token from query string
        query_string = parse_qs(scope["query_string"].decode())
        token = query_string.get("token")

        if not token:
            scope["user"] = AnonymousUser()
        else:
            try:
                access_token = AccessToken(token[0])
                user_id = access_token["user_id"]
                scope["user"] = await get_user(user_id)
            except Exception:
                scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
