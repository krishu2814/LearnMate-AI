from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthException,
    ForbiddenException,
    TokenExpiredException,
    TokenInvalidException,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_opaque_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.dependencies import get_current_active_superuser, get_current_user
from app.models.user import SkillLevel, User


def test_argon2_password_hashing():
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_token_creation_and_decoding():
    user_id = "user-uuid-12345"
    token = create_access_token(
        subject=user_id,
        extra_claims={"role": "student", "email": "test@example.com"},
    )

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "student"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expired_token():
    past_delta = timedelta(minutes=-10)
    token = create_access_token(subject="user-123", expires_delta=past_delta)

    with pytest.raises(TokenExpiredException):
        decode_access_token(token)


def test_jwt_invalid_or_tampered_token():
    token = create_access_token(subject="user-123")
    tampered_token = token[:-5] + "ABCDE"

    with pytest.raises(TokenInvalidException):
        decode_access_token(tampered_token)

    with pytest.raises(TokenInvalidException):
        decode_access_token("completely_malformed_token")


def test_opaque_refresh_token_generation_and_hashing():
    raw_token = generate_opaque_refresh_token()
    assert len(raw_token) >= 64
    assert isinstance(raw_token, str)

    hashed1 = hash_token(raw_token)
    hashed2 = hash_token(raw_token)
    assert len(hashed1) == 64  # SHA-256 produces 64 hex characters
    assert hashed1 == hashed2


@pytest.mark.asyncio
async def test_get_current_user_dependency(db_session: AsyncSession):
    # Create active user
    user = User(
        email=f"auth_{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("pw123"),
        full_name="Auth Test Student",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    valid_token = create_access_token(subject=user.id)
    retrieved_user = await get_current_user(token=valid_token, db=db_session)
    assert retrieved_user.id == user.id
    assert retrieved_user.email == user.email

    # Inactive user
    user.is_active = False
    await db_session.commit()

    with pytest.raises(AuthException) as exc_info:
        await get_current_user(token=valid_token, db=db_session)
    assert "inactive" in exc_info.value.message.lower()

    # Clean up
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_current_active_superuser_dependency():
    regular_user = User(
        email="student@example.com",
        password_hash="pw",
        is_superuser=False,
    )
    superuser = User(
        email="admin@example.com",
        password_hash="pw",
        is_superuser=True,
    )

    result = await get_current_active_superuser(superuser)
    assert result.is_superuser is True

    with pytest.raises(ForbiddenException):
        await get_current_active_superuser(regular_user)
