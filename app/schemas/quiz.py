from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType


class QuizQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    question_type: QuestionType
    options: list[str] | None = None
    position: int
    topic_tag: str | None = None


class QuizQuestionDetailResponse(QuizQuestionResponse):
    correct_answer: str
    explanation: str | None = None


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    topic: str
    difficulty: DifficultyLevel
    question_count: int
    lesson_id: str | None = None
    created_at: datetime


class QuizDetailResponse(QuizResponse):
    questions: list[QuizQuestionResponse] = Field(default_factory=list)


class QuizAnswerSubmit(BaseModel):
    question_id: str
    user_answer: str = Field(..., min_length=1, description="Selected option or text response")


class QuizAttemptCreate(BaseModel):
    answers: list[QuizAnswerSubmit] = Field(
        ..., min_length=1, description="List of submitted answers"
    )
    time_seconds: int = Field(
        default=0, ge=0, description="Duration in seconds taken for the attempt"
    )
    is_exam_mode: bool = Field(
        default=False, description="Whether the attempt was taken under exam conditions"
    )


class QuizAnswerResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: str
    user_answer: str
    is_correct: bool
    correct_answer: str
    explanation: str | None = None
    ai_confidence: float | None = None
    ai_feedback: str | None = None


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
    answers: list[QuizAnswerResultResponse] = Field(default_factory=list)


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
    items: list[QuizAttemptSummaryResponse]
