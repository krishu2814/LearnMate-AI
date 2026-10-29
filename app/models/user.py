import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.auth import RefreshToken
    from app.models.learning_path import LearningPath
    from app.models.progress import LessonProgress


class SkillLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    skill_level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, name="skill_level_enum", native_enum=False),
        default=SkillLevel.BEGINNER,
        nullable=False,
    )
    daily_study_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    learning_paths: Mapped[List["LearningPath"]] = relationship(
        "LearningPath",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    lesson_progress: Mapped[List["LessonProgress"]] = relationship(
        "LessonProgress",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __init__(
        self,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
        skill_level: SkillLevel = SkillLevel.BEGINNER,
        daily_study_minutes: int = 60,
        timezone: str = "UTC",
        is_active: bool = True,
        is_superuser: bool = False,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.skill_level = skill_level
        self.daily_study_minutes = daily_study_minutes
        self.timezone = timezone
        self.is_active = is_active
        self.is_superuser = is_superuser

    def __repr__(self) -> str:
        return f"<User {self.email} (id={self.id})>"
