import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    # Optional, not required: omitting it entirely (every other service's
    # test fixtures, or any future non-UI caller) leaves it null, same as
    # an existing pre-this-column user -- the real signup *form* always
    # collects it, but the API itself doesn't force every caller to.
    first_name: str | None = None

    @field_validator("first_name")
    @classmethod
    def _trim_and_reject_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("first_name cannot be blank")
        return trimmed


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ServiceTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class ServiceTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    # No refresh_token — a client secret is already a long-lived credential
    # (Decision #41); the client just re-requests with the same secret.
