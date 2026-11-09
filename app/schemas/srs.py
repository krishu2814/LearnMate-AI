from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType


class ReviewQuestionResponse(BaseModel):
    """Masked quiz question details for spaced repetition review."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    question_type: QuestionType
    options: list[str] | None = None
    topic_tag: str | None = None


class ReviewItemResponse(BaseModel):
    """Representation of an individual spaced repetition item due for review."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    topic_tag: str | None
    interval_days: int
    repetitions: int
    ease_factor: float
    next_review_at: datetime
    last_reviewed_at: datetime | None
    consecutive_correct: int
    question: ReviewQuestionResponse


class WeakTopicSummary(BaseModel):
    """Aggregated weak topic concept count."""

    topic: str
    missed_count: int


class ReviewQueueResponse(BaseModel):
    """Full Spaced Repetition queue for the learner."""

    model_config = ConfigDict(from_attributes=True)

    due_count: int
    total_tracked_count: int
    weak_topics: list[WeakTopicSummary] = []
    items: list[ReviewItemResponse] = []


class SubmitReviewRequest(BaseModel):
    """Student's answer submission for a due review item."""

    model_config = ConfigDict(extra="forbid")

    user_answer: str = Field(
        ..., min_length=1, description="Student's answer to the review question"
    )


class ReviewResultResponse(BaseModel):
    """Scored feedback and updated SM-2 scheduling parameters."""

    model_config = ConfigDict(from_attributes=True)

    item_id: str
    is_correct: bool
    correct_answer: str
    explanation: str | None
    new_interval_days: int
    new_repetitions: int
    next_review_at: datetime


class RemediationQuizRequest(BaseModel):
    """Request payload to generate a personalized remediation quiz targeting weak spots."""

    model_config = ConfigDict(extra="forbid")

    num_questions: int = Field(
        default=5, ge=2, le=15, description="Number of remediation questions"
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.INTERMEDIATE, description="Target difficulty"
    )
