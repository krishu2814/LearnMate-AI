import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.course import DifficultyLevel

if TYPE_CHECKING:
    from app.models.course import Lesson
    from app.models.user import User


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class Quiz(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quizzes"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="quiz_difficulty_enum", native_enum=False),
        default=DifficultyLevel.BEGINNER,
        nullable=False,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    lesson_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.position",
        lazy="selectin",
    )
    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizAttempt.submitted_at.desc()",
        lazy="selectin",
    )
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    lesson: Mapped[Optional["Lesson"]] = relationship("Lesson", foreign_keys=[lesson_id])

    def __init__(
        self,
        title: str,
        topic: str,
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        user_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        question_count: int = 0,
        prompt_version: Optional[str] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.title = title
        self.topic = topic
        self.difficulty = difficulty
        self.user_id = user_id
        self.lesson_id = lesson_id
        self.question_count = question_count
        self.prompt_version = prompt_version


class QuizQuestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quiz_questions"

    quiz_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type_enum", native_enum=False),
        default=QuestionType.MCQ,
        nullable=False,
    )
    options: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")

    def __init__(
        self,
        quiz_id: str,
        question: str,
        correct_answer: str,
        question_type: QuestionType = QuestionType.MCQ,
        options: Optional[List[str]] = None,
        explanation: Optional[str] = None,
        topic_tag: Optional[str] = None,
        position: int = 1,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.quiz_id = quiz_id
        self.question = question
        self.correct_answer = correct_answer
        self.question_type = question_type
        self.options = options
        self.explanation = explanation
        self.topic_tag = topic_tag
        self.position = position


class QuizAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quiz_attempts"

    quiz_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_exam_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")
    answers: Mapped[List["QuizAnswer"]] = relationship(
        "QuizAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __init__(
        self,
        quiz_id: str,
        user_id: str,
        score: float = 0.0,
        total_questions: int = 0,
        correct_count: int = 0,
        time_seconds: int = 0,
        is_exam_mode: bool = False,
        submitted_at: Optional[datetime] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.quiz_id = quiz_id
        self.user_id = user_id
        self.score = score
        self.total_questions = total_questions
        self.correct_count = correct_count
        self.time_seconds = time_seconds
        self.is_exam_mode = is_exam_mode
        self.submitted_at = submitted_at or datetime.now(timezone.utc)


class QuizAnswer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quiz_answers"

    attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    attempt: Mapped["QuizAttempt"] = relationship("QuizAttempt", back_populates="answers")
    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", lazy="selectin")

    def __init__(
        self,
        attempt_id: str,
        question_id: str,
        user_answer: str,
        is_correct: bool = False,
        ai_confidence: Optional[float] = None,
        ai_feedback: Optional[str] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.attempt_id = attempt_id
        self.question_id = question_id
        self.user_answer = user_answer
        self.is_correct = is_correct
        self.ai_confidence = ai_confidence
        self.ai_feedback = ai_feedback
