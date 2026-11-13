import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class GamificationProfile(Base, UUIDMixin, TimestampMixin):
    """Stores student XP, level progression, and daily active study streaks."""

    __tablename__ = "gamification_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    total_xp: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    current_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="gamification_profile",
    )

    def __init__(
        self,
        user_id: str,
        total_xp: int = 0,
        current_level: int = 1,
        current_streak: int = 0,
        longest_streak: int = 0,
        last_active_date: datetime.date | None = None,
        id: str | None = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.total_xp = total_xp
        self.current_level = current_level
        self.current_streak = current_streak
        self.longest_streak = longest_streak
        self.last_active_date = last_active_date

    def __repr__(self) -> str:
        return f"<GamificationProfile user={self.user_id} level={self.current_level} xp={self.total_xp} streak={self.current_streak}d>"


class Badge(Base, TimestampMixin):
    """Defines an achievement badge that can be unlocked by learners."""

    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(100), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    criteria_type: Mapped[str] = mapped_column(String(50), nullable=False)
    criteria_threshold: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    user_badges: Mapped[list["UserBadge"]] = relationship(
        "UserBadge",
        back_populates="badge",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        icon: str,
        xp_reward: int = 50,
        criteria_type: str = "custom",
        criteria_threshold: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.xp_reward = xp_reward
        self.criteria_type = criteria_type
        self.criteria_threshold = criteria_threshold

    def __repr__(self) -> str:
        return f"<Badge id={self.id} name='{self.name}' xp={self.xp_reward}>"


class UserBadge(Base, UUIDMixin, TimestampMixin):
    """Represents a badge unlocked by an individual student."""

    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    badge_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("badges.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    unlocked_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="badges",
    )
    badge: Mapped["Badge"] = relationship(
        "Badge",
        back_populates="user_badges",
        lazy="joined",
    )

    def __init__(
        self,
        user_id: str,
        badge_id: str,
        unlocked_at: datetime.datetime | None = None,
        id: str | None = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.badge_id = badge_id
        self.unlocked_at = unlocked_at or datetime.datetime.now(datetime.UTC)

    def __repr__(self) -> str:
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"
