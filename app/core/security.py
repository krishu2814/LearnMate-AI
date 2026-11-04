import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.core.exceptions import TokenExpiredException, TokenInvalidException

# Argon2id password hasher with OWASP-recommended parameters
password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
)


def hash_password(plain_password: str) -> str:
    """Hash password using memory-hard Argon2id algorithm."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create short-lived JWT access token (default 15 minutes)."""
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except ExpiredSignatureError as exc:
        raise TokenExpiredException("Access token has expired") from exc
    except JWTError as exc:
        raise TokenInvalidException("Could not validate credentials or token is malformed") from exc


def generate_opaque_refresh_token() -> str:
    """Generate a high-entropy 64-byte URL-safe opaque string."""
    return secrets.token_urlsafe(64)


def hash_token(raw_token: str) -> str:
    """Hash opaque token with SHA-256 before persisting to database."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
