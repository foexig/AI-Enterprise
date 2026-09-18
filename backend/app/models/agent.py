from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import Role

# Zuordnungstabelle Agent <-> Role (welche Rollen Zugriff auf den Agent haben)
agent_roles = Table(
    "agent_roles",
    Base.metadata,
    Column("agent_id", Integer, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Serverseitiger System-Prompt; wird normalen Benutzern NIEMALS ausgeliefert
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Zentrale Modellkonfiguration (Foundation-Model-ID oder Inference-Profile-ARN)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    roles: Mapped[list[Role]] = relationship(
        "Role", secondary=agent_roles, back_populates="agents", lazy="selectin"
    )


# Rückseite der Beziehung auf der Role
Role.agents = relationship("Agent", secondary=agent_roles, back_populates="roles", lazy="selectin")
