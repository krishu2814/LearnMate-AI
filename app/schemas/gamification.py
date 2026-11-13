from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BadgeResponse(BaseModel):
    """Achievement badge representation with user unlock state."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique badge identifier")
    name: str = Field(..., description="Badge display name")
    description: str = Field(..., description="Achievement criteria description")
    icon: str = Field(..., description="Visual badge icon or emoji")
    xp_reward: int = Field(..., description="XP granted when unlocking this badge")
    criteria_type: str = Field(..., description="Evaluation metric type")
    criteria_threshold: int = Field(..., description="Threshold count required to unlock")
    is_unlocked: bool = Field(default=False, description="Whether the user has earned this badge")
    unlocked_at: datetime | None = Field(
        default=None,
        description="Timestamp when badge was unlocked, if applicable",
    )


class GamificationProfileResponse(BaseModel):
    """Comprehensive gamification profile for a learner."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    total_xp: int = Field(..., description="Cumulative experience points earned")
    current_level: int = Field(..., description="Learner level computed from total XP")
    current_level_base_xp: int = Field(..., description="XP threshold for current level")
    next_level_xp: int = Field(..., description="XP threshold to reach next level")
    xp_for_next_level: int = Field(..., description="Remaining XP required to reach next level")
    level_progress_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage completion toward next level",
    )
    current_streak: int = Field(..., description="Consecutive active study days")
    longest_streak: int = Field(..., description="All-time longest study streak")
    last_active_date: date | None = Field(
        default=None, description="Date of last recorded activity"
    )
    unlocked_badges_count: int = Field(..., description="Number of unlocked badges")
    total_badges_count: int = Field(..., description="Total badges available in the platform")
    recent_badges: list[BadgeResponse] = Field(
        default=[],
        description="Recently unlocked badges (up to 5)",
    )


class LeaderboardEntry(BaseModel):
    """Ranked leaderboard standing for a learner."""

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., ge=1, description="Leaderboard placement")
    user_id: str = Field(..., description="User ID")
    full_name: str = Field(default="Anonymous Learner", description="Learner display name")
    total_xp: int = Field(..., description="Total XP")
    current_level: int = Field(..., description="Current level")
    current_streak: int = Field(..., description="Current active streak in days")
    badges_count: int = Field(..., description="Count of earned badges")


class LeaderboardResponse(BaseModel):
    """Global or course-level leaderboard response."""

    entries: list[LeaderboardEntry] = Field(default=[], description="Top learners ranked by XP")
    user_rank: int | None = Field(default=None, description="Current authenticated user's rank")
    user_entry: LeaderboardEntry | None = Field(
        default=None,
        description="Current authenticated user's leaderboard record",
    )


class SyncGamificationResponse(BaseModel):
    """Result of synchronizing user learning progress with gamification progression."""

    xp_awarded: int = Field(..., description="XP points awarded during this synchronization")
    newly_unlocked_badges: list[BadgeResponse] = Field(
        default=[],
        description="Badges newly unlocked during this sync",
    )
    profile: GamificationProfileResponse = Field(..., description="Updated gamification profile")
    message: str = Field(..., description="Human-readable sync summary")
