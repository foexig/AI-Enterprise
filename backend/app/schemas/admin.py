from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Benutzer-Verwaltung ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    role_ids: list[int] = []
    is_admin: bool = False


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    is_admin: bool | None = None
    role_ids: list[int] | None = None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    is_active: bool
    is_admin: bool
    roles: list[str]
    created_at: datetime


# --- Rollen ---
class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# --- Agents (vollständige Konfiguration nur für Admins) ---
class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = ""
    system_prompt: str = ""
    model_id: str = Field(min_length=1, max_length=255)
    role_ids: list[int] = []
    is_active: bool = True


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = None
    system_prompt: str | None = None
    model_id: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class AdminAgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    system_prompt: str
    model_id: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class AgentRolesUpdate(BaseModel):
    role_ids: list[int]
