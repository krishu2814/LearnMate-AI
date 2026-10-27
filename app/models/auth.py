import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    device_info: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    def __init__(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        revoked_at: Optional[datetime] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.device_info = device_info
        self.revoked_at = revoked_at

    @property
    def is_active(self) -> bool:
        """Token is active if not revoked and has not expired."""
        now = datetime.now(timezone.utc)
        expires = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return self.revoked_at is None and expires > now

    def revoke(self) -> None:
        """Mark token as revoked."""
        self.revoked_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} active={self.is_active}>"
