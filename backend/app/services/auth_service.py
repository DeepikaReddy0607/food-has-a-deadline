from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserSummary,
    UserPublicResponse,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.core.config import settings


class AuthService:
    @staticmethod
    def register(db: Session, req: UserRegisterRequest) -> User:
        # Check if user already exists
        existing_user = UserRepository.get_by_email(db, req.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

        # Hash password with Argon2id
        hashed_pw = hash_password(req.password)

        # Create user
        user = UserRepository.create(
            db=db,
            email=req.email,
            hashed_password=hashed_pw,
            role=req.role,
        )
        return user

    @staticmethod
    def login(db: Session, req: UserLoginRequest) -> TokenResponse:
        user = UserRepository.get_by_email(db, req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )

        token = create_access_token(
            subject=user.id,
            role=user.role,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user=UserSummary(
                id=user.id,
                email=user.email,
                role=user.role,
            ),
        )

    @staticmethod
    def build_user_public_response(user: User) -> UserPublicResponse:
        profile_data: Optional[Dict[str, Any]] = None
        if user.supplier_profile:
            profile_data = {
                "profile_type": "SUPPLIER",
                "id": str(user.supplier_profile.id),
                "organization_name": user.supplier_profile.organization_name,
                "contact_phone": user.supplier_profile.contact_phone,
                "address": user.supplier_profile.address,
                "facility_type": user.supplier_profile.facility_type,
                "latitude": float(user.supplier_profile.latitude),
                "longitude": float(user.supplier_profile.longitude),
            }
        elif user.receiver_profile:
            profile_data = {
                "profile_type": "RECEIVER",
                "id": str(user.receiver_profile.id),
                "organization_name": user.receiver_profile.organization_name,
                "contact_phone": user.receiver_profile.contact_phone,
                "address": user.receiver_profile.address,
                "capacity_daily_kg": float(user.receiver_profile.capacity_daily_kg),
                "priority_level": user.receiver_profile.priority_level,
                "latitude": float(user.receiver_profile.latitude),
                "longitude": float(user.receiver_profile.longitude),
            }

        return UserPublicResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            profile=profile_data,
        )
