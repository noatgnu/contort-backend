from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session

@database_sync_to_async
def get_user(token):
    try:
        return Token.objects.get(key=token).user
    except Token.DoesNotExist:
        return AnonymousUser()

@database_sync_to_async
def get_user_by_session_id(session_id):
    try:
        session = Session.objects.get(session_key=session_id)
        uid = session.get_decoded().get('_auth_user_id')
        return User.objects.get(pk=uid)
    except (Session.DoesNotExist, User.DoesNotExist):
        return AnonymousUser()

class TokenAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        try:
            token_key = (dict((x.split('=') for x in scope['query_string'].decode().split("&")))).get('token', None)
        except ValueError:
            token_key = None
        scope['user'] = AnonymousUser() if token_key is None else await get_user(token_key)
        # if scope['user'] is AnonymousUser() try using token_key with get_user_by_session_id
        if isinstance(scope['user'], AnonymousUser):
            scope['user'] = await get_user_by_session_id(token_key)

        return await super().__call__(scope, receive, send)