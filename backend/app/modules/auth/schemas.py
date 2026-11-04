from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.currencies import validate_currency


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    default_currency: str = "USD"

    def validated_currency(self) -> str:
        return validate_currency(self.default_currency)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    photo_url: str | None = Field(default=None, max_length=512)
    default_currency: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    photo_url: str | None
    default_currency: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
