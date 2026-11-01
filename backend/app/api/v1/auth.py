from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserPublicResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Register a new SUPPLIER or RECEIVER account. Public registration as ADMIN or COORDINATOR is forbidden.",
)
def register(
    req: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    user = AuthService.register(db, req)
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "message": "Account registered successfully.",
    }


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT",
    description="Authenticate with email and password to receive a Bearer JWT access token.",
)
def login(
    req: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return AuthService.login(db, req)


@router.get(
    "/me",
    response_model=UserPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description="Retrieve account details and public profile for the authenticated user.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserPublicResponse:
    return AuthService.build_user_public_response(current_user)
