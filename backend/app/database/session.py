from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.x declarative models."""
    pass


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=(settings.ENVIRONMENT == "development"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing an isolated database session with auto-close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """Check connectivity to PostgreSQL database without throwing unhandled exceptions."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            if result == 1:
                return {
                    "status": "connected",
                    "connected": True,
                    "details": "PostgreSQL database connection verified",
                }
            return {
                "status": "unexpected_result",
                "connected": False,
                "details": f"Unexpected query response: {result}",
            }
    except Exception as exc:
        return {
            "status": "disconnected",
            "connected": False,
            "details": f"Database unreachable: {type(exc).__name__}",
        }
