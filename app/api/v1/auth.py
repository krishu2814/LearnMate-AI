from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
async def register(
    payload: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    auth_service = AuthService(db)
    return await auth_service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and obtain access + refresh tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    auth_service = AuthService(db)
    device_info = user_agent or request.client.host if request.client else "Unknown"
    return await auth_service.login(payload, device_info=device_info)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and get a fresh access token",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    auth_service = AuthService(db)
    device_info = user_agent or request.client.host if request.client else "Unknown"
    return await auth_service.refresh_token(payload.refresh_token, device_info=device_info)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token session",
)
async def logout(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    auth_service = AuthService(db)
    await auth_service.logout(payload.refresh_token)
