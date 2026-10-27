from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.auth import RefreshToken
from app.models.user import SkillLevel, User


def test_user_model_defaults():
    user = User(
        email="test@example.com",
        password_hash="argon2_hashed_secret",
        full_name="Test Student",
    )
    assert user.email == "test@example.com"
    assert user.skill_level == SkillLevel.BEGINNER
    assert user.daily_study_minutes == 60
    assert user.timezone == "UTC"
    assert user.is_active is True
    assert user.is_superuser is False
    assert len(user.id) == 36  # UUID string format


def test_refresh_token_active_and_revocation():
    future = datetime.now(timezone.utc) + timedelta(days=7)
    past = datetime.now(timezone.utc) - timedelta(days=1)

    active_token = RefreshToken(
        user_id="user-123",
        token_hash="fakehash123",
        expires_at=future,
    )
    assert active_token.is_active is True

    expired_token = RefreshToken(
        user_id="user-123",
        token_hash="fakehash456",
        expires_at=past,
    )
    assert expired_token.is_active is False

    active_token.revoke()
    assert active_token.is_active is False
    assert active_token.revoked_at is not None


@pytest.mark.asyncio
async def test_user_and_refresh_token_db_relationship(db_session: AsyncSession):
    user_email = f"student_{datetime.now().timestamp()}@example.com"
    user = User(
        email=user_email,
        password_hash="dummy_hashed_pw",
        full_name="Relationship Test User",
        skill_level=SkillLevel.INTERMEDIATE,
    )
    db_session.add(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=user.id,
        token_hash=f"hash_{datetime.now().timestamp()}",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        device_info="Chrome / macOS",
    )
    db_session.add(token)
    await db_session.commit()

    # Query user with tokens
    stmt = select(User).where(User.id == user.id)
    result = await db_session.execute(stmt)
    queried_user = result.scalar_one_or_none()

    assert queried_user is not None
    assert queried_user.email == user_email
    assert len(queried_user.refresh_tokens) == 1
    assert queried_user.refresh_tokens[0].token_hash == token.token_hash
    assert queried_user.refresh_tokens[0].is_active is True

    # Clean up test user (cascade should remove token)
    await db_session.delete(queried_user)
    await db_session.commit()
