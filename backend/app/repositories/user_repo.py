import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User, SupplierProfile, ReceiverProfile


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        return db.scalar(select(User).where(User.id == user_id))

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.scalar(select(User).where(User.email == email.lower().strip()))

    @staticmethod
    def create(
        db: Session,
        email: str,
        hashed_password: str,
        role: str,
    ) -> User:
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            role=role,
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
