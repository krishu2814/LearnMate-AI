from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.course import DifficultyLevel


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    module_id: str
    title: str
    estimated_minutes: int
    position: int


class LessonDetailResponse(LessonResponse):
    content: str


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    position: int
    summary: Optional[str] = None
    lessons: List[LessonResponse] = []


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    subject_tag: str
    difficulty: DifficultyLevel
    is_published: bool


class CourseDetailResponse(CourseResponse):
    modules: List[ModuleResponse] = []
