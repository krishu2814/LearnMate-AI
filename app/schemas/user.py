
from pydantic import BaseModel, Field

from app.models.user import SkillLevel


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=150)
    skill_level: SkillLevel | None = None
    daily_study_minutes: int | None = Field(None, ge=15, le=480)
    timezone: str | None = Field(None, max_length=50)
