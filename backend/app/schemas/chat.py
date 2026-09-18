from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageSendResponse(BaseModel):
    """Antwort auf eine gesendete Nachricht inkl. Token-Nutzung (Kostenüberwachung)."""

    message: MessageOut
    input_tokens: int
    output_tokens: int
    model_id: str
