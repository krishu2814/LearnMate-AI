from typing import Optional
from pydantic import BaseModel, Field

from app.models.user import SkillLevel


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=150)
    skill_level: Optional[SkillLevel] = None
    daily_study_minutes: Optional[int] = Field(None, ge=15, le=480)
    timezone: Optional[str] = Field(None, max_length=50)
