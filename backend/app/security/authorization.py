from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models import Agent, User
from app.utils import utcnow


def get_agent_for_user(db: Session, user: User, agent_id: int) -> Agent:
    """Zentrale serverseitige Berechtigungsprüfung für Agent-Zugriff.

    Prüft in dieser Reihenfolge:
      1. Existiert der Agent?            -> 404 (kein Bestands-Enumeration-Leak)
      2. Ist der Agent aktiv?            -> 403
      3. Hat der Benutzer eine Rolle,
         die Zugriff erlaubt?             -> 403

    Diese Prüfung läuft bei JEDEM geschützten Endpoint erneut (auch beim
    Senden einer Nachricht), nie nur im Frontend.
    """
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Agent nicht gefunden")

    if not agent.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Agent ist deaktiviert")

    user_role_ids = {role.id for role in user.roles}
    agent_role_ids = {role.id for role in agent.roles}
    if not user_role_ids & agent_role_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf diesen Agent")

    return agent


def get_owned_session(db: Session, user: User, session_id: int):
    """Lädt eine ChatSession, die dem aktuellen Benutzer gehören muss (404 sonst)."""
    from app.models import ChatSession

    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        # 404 statt 403: existierende Session-IDs anderer Benutzer nicht aufdeckbar
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session nicht gefunden")
    return session


def ensure_session_valid(chat_session) -> None:
    """Wirft 403, wenn die Session abgelaufen ist (TTL)."""
    if chat_session.expires_at <= utcnow():
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Session abgelaufen. Bitte starten Sie eine neue Session.")
