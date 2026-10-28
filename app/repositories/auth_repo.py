from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import RefreshToken


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_refresh_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_token(self, token: RefreshToken) -> None:
        token.revoke()
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: str) -> int:
        """
        Token Reuse Detection: Revoke all active tokens for a compromised user account.
        Returns the number of tokens updated.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
