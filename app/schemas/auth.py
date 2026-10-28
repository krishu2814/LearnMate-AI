from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import SkillLevel


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")
    full_name: Optional[str] = Field(None, max_length=150)
    skill_level: SkillLevel = SkillLevel.BEGINNER
    daily_study_minutes: int = Field(default=60, ge=15, le=480)
    timezone: str = Field(default="UTC", max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    skill_level: SkillLevel
    daily_study_minutes: int
    timezone: str
    is_active: bool
    created_at: datetime
