from datetime import timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Agent, ChatSession, User
from app.schemas.agent import AgentOut
from app.schemas.chat import SessionOut
from app.security.authorization import get_agent_for_user
from app.security.deps import get_current_user
from app.utils import utcnow

router = APIRouter(prefix="/agents", tags=["Agents"])
settings = get_settings()


@router.get("", response_model=list[AgentOut])
def list_agents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Alle aktiven Agents, für die der Benutzer durch seine Rollen freigeschaltet ist.

    Ausgabe enthält KEINE System-Prompts und KEINE internen Konfigurationen.
    """
    user_role_ids = {r.id for r in user.roles}
    agents = db.query(Agent).filter(Agent.is_active.is_(True)).all()
    return [
        AgentOut.model_validate(agent)
        for agent in agents
        if user_role_ids & {r.id for r in agent.roles}
    ]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Einzelnen Agent abrufen - MIT serverseitiger Berechtigungsprüfung (403/404)."""
    agent = get_agent_for_user(db, user, agent_id)
    return AgentOut.model_validate(agent)


@router.post("/{agent_id}/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Neue Chat-Session für einen Agent (Berechtigungsprüfung inklusive).

    Eindeutigkeit: user_id + agent_id + session_id. Kein globaler Kontext.
    """
    agent = get_agent_for_user(db, user, agent_id)

    chat_session = ChatSession(
        user_id=user.id,
        agent_id=agent.id,
        expires_at=utcnow() + timedelta(hours=settings.SESSION_TTL_HOURS),
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


@router.get("/{agent_id}/sessions", response_model=list[SessionOut])
def list_sessions(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sessions des aktuellen Benutzers für einen Agent (nur eigene, neueste zuerst)."""
    get_agent_for_user(db, user, agent_id)
    return (
        db.query(ChatSession)
        .filter(ChatSession.agent_id == agent_id, ChatSession.user_id == user.id)
        .order_by(ChatSession.last_activity_at.desc())
        .limit(50)
        .all()
    )
