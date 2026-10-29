from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.learning_path import ItemType, PathStatus


class LearningPathItemCreate(BaseModel):
    lesson_id: str
    position: int = Field(default=1, ge=1)
    item_type: ItemType = ItemType.LESSON
    is_optional: bool = False


class LearningPathItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    learning_path_id: str
    lesson_id: str
    lesson_title: str = ""
    estimated_minutes: int = 0
    position: int
    item_type: ItemType
    is_optional: bool
    is_completed: bool


class LearningPathCreate(BaseModel):
    title: str = Field(..., max_length=200)
    goal: str
    total_days: int = Field(default=30, ge=1, le=365)
    daily_minutes: int = Field(default=60, ge=15, le=480)
    lesson_ids: List[str] = Field(default=[], description="Ordered list of lesson IDs to include")


class LearningPathUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    goal: Optional[str] = None
    status: Optional[PathStatus] = None
    total_days: Optional[int] = Field(None, ge=1, le=365)
    daily_minutes: Optional[int] = Field(None, ge=15, le=480)


class LearningPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    goal: str
    status: PathStatus
    total_days: int
    daily_minutes: int
    created_at: datetime
    total_items: int = 0
    completed_items: int = 0
    completion_pct: float = 0.0


class LearningPathDetailResponse(LearningPathResponse):
    items: List[LearningPathItemResponse] = []
