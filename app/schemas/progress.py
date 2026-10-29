from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.progress import ProgressStatus


class LessonProgressUpdate(BaseModel):
    status: ProgressStatus = Field(default=ProgressStatus.COMPLETED)
    time_spent_seconds: Optional[int] = Field(None, ge=0, description="Total seconds spent on lesson")
    additional_seconds: Optional[int] = Field(0, ge=0, description="Seconds to add to cumulative time spent")


class LessonProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    lesson_id: str
    status: ProgressStatus
    time_spent_seconds: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CourseProgressSummary(BaseModel):
    course_id: str
    course_title: str
    total_lessons: int
    completed_lessons: int
    completion_pct: float


class PathProgressSummary(BaseModel):
    path_id: str
    title: str
    total_items: int
    completed_items: int
    completion_pct: float


class DashboardProgressResponse(BaseModel):
    total_lessons_available: int
    completed_lessons: int
    in_progress_lessons: int
    overall_completion_pct: float
    total_time_spent_seconds: int
    total_time_spent_minutes: int
    courses_progress: List[CourseProgressSummary] = []
    active_paths_progress: List[PathProgressSummary] = []
