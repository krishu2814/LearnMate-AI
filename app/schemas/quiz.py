from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType


class QuizQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    position: int
    topic_tag: Optional[str] = None


class QuizQuestionDetailResponse(QuizQuestionResponse):
    correct_answer: str
    explanation: Optional[str] = None


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    topic: str
    difficulty: DifficultyLevel
    question_count: int
    lesson_id: Optional[str] = None
    created_at: datetime


class QuizDetailResponse(QuizResponse):
    questions: List[QuizQuestionResponse] = Field(default_factory=list)


class QuizAnswerSubmit(BaseModel):
    question_id: str
    user_answer: str = Field(..., min_length=1, description="Selected option or text response")


class QuizAttemptCreate(BaseModel):
    answers: List[QuizAnswerSubmit] = Field(..., min_length=1, description="List of submitted answers")
    time_seconds: int = Field(default=0, ge=0, description="Duration in seconds taken for the attempt")
    is_exam_mode: bool = Field(default=False, description="Whether the attempt was taken under exam conditions")


class QuizAnswerResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: str
    user_answer: str
    is_correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_feedback: Optional[str] = None


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quiz_id: str
    user_id: str
    score: float
    total_questions: int
    correct_count: int
    time_seconds: int
    is_exam_mode: bool
    submitted_at: datetime
    answers: List[QuizAnswerResultResponse] = Field(default_factory=list)


class QuizAttemptSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quiz_id: str
    score: float
    total_questions: int
    correct_count: int
    time_seconds: int
    is_exam_mode: bool
    submitted_at: datetime


class PaginatedQuizAttemptsResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[QuizAttemptSummaryResponse]
