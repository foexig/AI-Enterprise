import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.security.deps import get_current_user
from app.security.password import verify_password
from app.security.tokens import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Anmeldung mit E-Mail + Passwort. Keine Auskunft darüber, ob E-Mail existiert."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        # Einheitliche Meldung: kein User-Enumeration
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="E-Mail oder Passwort falsch")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Benutzerkonto ist deaktiviert")

    logger.info("Login erfolgreich: user_id=%s", user.id)
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            roles=[r.name for r in user.roles],
            created_at=user.created_at,
        ),
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    """Logout. JWT ist zustandslos: der Client verwirft den Token.

    Für eine serverseitige Token-Sperrung (Revocation List) kann später ein
    Blacklist-Mechanismus ergänzt werden; die Architektur bleibt davon unberührt.
    """
    return {"detail": "Erfolgreich abgemeldet"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Aktueller Benutzer inklusive seiner Rollen (Namen, keine Metadaten)."""
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        roles=[r.name for r in user.roles],
        created_at=user.created_at,
    )
