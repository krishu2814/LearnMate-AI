from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthException, ConflictException
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    generate_opaque_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserRegister, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.auth_repo = AuthRepository(db)

    async def register(self, data: UserRegister) -> UserResponse:
        """Register a new student account."""
        existing_user = await self.user_repo.get_by_email(data.email)
        if existing_user:
            raise ConflictException(f"User with email '{data.email}' already exists")

        hashed_password = hash_password(data.password)
        user = await self.user_repo.create(
            email=data.email,
            password_hash=hashed_password,
            full_name=data.full_name,
            skill_level=data.skill_level,
            daily_study_minutes=data.daily_study_minutes,
            timezone=data.timezone,
        )

        logger.info("user_registered", user_id=user.id, email=user.email)
        return UserResponse.model_validate(user)

    async def login(
        self,
        data: LoginRequest,
        device_info: Optional[str] = None,
    ) -> TokenResponse:
        """Authenticate user credentials and issue access + refresh tokens."""
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise AuthException("Incorrect email or password")

        if not user.is_active:
            raise AuthException("User account has been deactivated")

        return await self._issue_token_pair(user_id=user.id, device_info=device_info)

    async def refresh_token(
        self,
        raw_refresh_token: str,
        device_info: Optional[str] = None,
    ) -> TokenResponse:
        """
        Rotate refresh token with automated token reuse detection.
        If a previously revoked token is reused, revoke ALL sessions for that user.
        """
        hashed_input = hash_token(raw_refresh_token)
        stored_token = await self.auth_repo.get_by_token_hash(hashed_input)

        if not stored_token:
            raise AuthException("Invalid or unrecognized refresh token")

        # Reuse detection: An already-revoked token was presented!
        if stored_token.revoked_at is not None:
            revoked_count = await self.auth_repo.revoke_all_for_user(stored_token.user_id)
            await self.db.commit()
            logger.warning(
                "token_reuse_detected",
                user_id=stored_token.user_id,
                revoked_sessions=revoked_count,
            )
            raise AuthException("Security alert: Token reuse detected. All active sessions have been terminated.")

        if not stored_token.is_active:
            raise AuthException("Refresh token has expired. Please log in again.")

        user = await self.user_repo.get_by_id(stored_token.user_id)
        if not user or not user.is_active:
            raise AuthException("Associated user account is no longer active")

        # Revoke the presented token (Rotation)
        await self.auth_repo.revoke_token(stored_token)

        # Issue a brand new pair
        logger.info("token_rotated", user_id=user.id)
        return await self._issue_token_pair(user_id=user.id, device_info=device_info)

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke the given refresh token."""
        hashed_input = hash_token(raw_refresh_token)
        stored_token = await self.auth_repo.get_by_token_hash(hashed_input)
        if stored_token and stored_token.revoked_at is None:
            await self.auth_repo.revoke_token(stored_token)
            logger.info("user_logged_out", user_id=stored_token.user_id)

    async def _issue_token_pair(
        self,
        user_id: str,
        device_info: Optional[str] = None,
    ) -> TokenResponse:
        """Helper to issue a fresh JWT access token and save a hashed refresh token."""
        now = datetime.now(timezone.utc)
        expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        access_token = create_access_token(
            subject=user_id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        raw_refresh_token = generate_opaque_refresh_token()
        hashed_refresh = hash_token(raw_refresh_token)
        refresh_expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.auth_repo.create_refresh_token(
            user_id=user_id,
            token_hash=hashed_refresh,
            expires_at=refresh_expires,
            device_info=device_info,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=expires_in_seconds,
        )
