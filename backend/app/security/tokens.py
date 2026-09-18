"""
Token-Erzeugung und -Validierung.

Die Authentifizierung ist bewusst an einer Stelle gekapselt (create_access_token /
get_current_user in security/deps.py), damit später ein externer Identity Provider
(AWS Cognito, Microsoft Entra ID) integriert werden kann, ohne die Endpoints
zu ändern: nur die Token-Validierung und die User-Synchronisation müssen dann
ausgetauscht bzw. ergänzt werden.
"""

from datetime import timedelta

import jwt

from app.config import get_settings
from app.utils import utcnow

settings = get_settings()


def create_access_token(user_id: int) -> str:
    expires = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Wirft jwt.PyJWTError bei ungültigem/abgelaufenem Token."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
