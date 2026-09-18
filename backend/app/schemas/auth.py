from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class UserOut(BaseModel):
    """Öffentliche Benutzerdaten - enthält niemals Passwort-Hashes."""

    id: int
    email: str
    name: str
    is_active: bool
    is_admin: bool
    roles: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
