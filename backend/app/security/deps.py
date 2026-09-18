import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, User
from app.security.tokens import decode_access_token

# auto_error=False: Wir erzeugen selbst kontrollierte 401-Antworten
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    """Authentifiziert den Benutzer anhand des Bearer-Tokens (serverseitig)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Nicht authentifiziert")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Ungültiger oder abgelaufener Token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Benutzer nicht gefunden oder deaktiviert")

    request.state.user_id = user.id
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Schützt Admin-Endpunkte serverseitig."""
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin-Berechtigung erforderlich")
    return user
