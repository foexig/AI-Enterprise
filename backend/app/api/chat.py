import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ChatMessage, ChatSession, UsageRecord, User
from app.schemas.chat import MessageCreate, MessageOut, MessageSendResponse, SessionOut
from app.security.authorization import (
    ensure_session_valid,
    get_agent_for_user,
    get_owned_session,
)
from app.security.deps import get_current_user
from app.services.bedrock_service import BedrockError, get_bedrock_service
from app.services.knowledge_service import KnowledgeService
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Chat"])
settings = get_settings()

knowledge_service = KnowledgeService()


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nachrichten einer Session - nur für den Eigentümer (fremde IDs -> 404)."""
    chat_session = get_owned_session(db, user, session_id)
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == chat_session.id)
        .order_by(ChatMessage.id.asc())
        .limit(500)
        .all()
    )


@router.post("/{session_id}/messages", response_model=MessageSendResponse)
def send_message(
    session_id: int,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nachricht senden und AI-Antwort erhalten.

    Serverseitige Prüfungen (in dieser Reihenfolge):
      1. Authentifiziert?                        -> 401 (Dependency)
      2. Session gehört dem Benutzer?            -> 404
      3. Agent existiert, ist aktiv und
         der Benutzer hat weiterhin Zugriff?      -> 403
      4. Session abgelaufen (TTL)?               -> 403

    Der Chat-Kontext besteht AUSSCHLIESSLICH aus den Nachrichten dieser
    Session (max. MAX_HISTORY_MESSAGES). Es gibt keinen globalen
    Unternehmens-Kontext.
    """
    chat_session = get_owned_session(db, user, session_id)
    agent = get_agent_for_user(db, user, chat_session.agent_id)
    ensure_session_valid(chat_session)

    # 1. Benutzerfrage persistieren
    user_message = ChatMessage(session_id=chat_session.id, role="user", content=payload.content)
    db.add(user_message)
    db.flush()

    # 2. Session-Kontext aufbauen (nur diese Session!)
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == chat_session.id)
        .order_by(ChatMessage.id.desc())
        .limit(settings.MAX_HISTORY_MESSAGES)
        .all()
    )
    history.reverse()
    messages = [{"role": m.role, "content": m.content} for m in history]

    # 3. RAG-Andockpunkt (MVP: liefert keine Fragmente)
    # knowledge_fragments = knowledge_service.retrieve(agent, payload.content)
    # -> später: Fragmente als Kontext an die Anfrage anreichern

    # 4. Bedrock-Aufruf (system_prompt + model_id kommen serverseitig aus der DB)
    bedrock = get_bedrock_service()
    try:
        result = bedrock.generate_response(
            system_prompt=agent.system_prompt,
            messages=messages,
            model_id=agent.model_id,
        )
    except BedrockError:
        logger.warning("Bedrock-Fehler: user_id=%s agent_id=%s", user.id, agent.id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="AI-Dienst momentan nicht verfügbar")

    # 5. Antwort persistieren + Session-Lebensdauer verlängern (Sliding TTL)
    assistant_message = ChatMessage(
        session_id=chat_session.id, role="assistant", content=result.text
    )
    db.add(assistant_message)
    chat_session.last_activity_at = utcnow()
    chat_session.expires_at = utcnow() + timedelta(hours=settings.SESSION_TTL_HOURS)
    db.flush()

    # 6. Token-Nutzung erfassen (Kostenüberwachung pro Agent/Team/Modell)
    db.add(
        UsageRecord(
            agent_id=agent.id,
            user_id=user.id,
            model_id=agent.model_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    )
    db.commit()
    db.refresh(assistant_message)

    # Logging OHNE Chat-Inhalte (Datenschutz)
    logger.info(
        "Chat: user_id=%s agent_id=%s session_id=%s in=%s out=%s",
        user.id, agent.id, chat_session.id, result.input_tokens, result.output_tokens,
    )

    return MessageSendResponse(
        message=MessageOut.model_validate(assistant_message),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model_id=agent.model_id,
    )
