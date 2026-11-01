from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Food Has a Deadline"
    TAGLINE: str = "Move food before time runs out."
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/food_has_a_deadline"

    # Security & Auth
    SECRET_KEY: str = "fhd-dev-insecure-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Google Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # CORS / Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        """
        Derives the explicit list of allowed CORS origins.
        Always includes the production Cloudflare Workers frontend and local development origins.
        Also parses any additional comma-separated origins from the FRONTEND_URL environment variable.
        """
        origins = [
            "https://food-has-a-deadline.deepikareddyrudru.workers.dev",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        if self.FRONTEND_URL:
            for url in self.FRONTEND_URL.split(","):
                cleaned = url.strip().rstrip("/")
                if cleaned and cleaned not in origins:
                    origins.append(cleaned)
        return origins

    # Geospatial & Routing
    OSRM_BASE_URL: str = "http://router.project-osrm.org"
    OSRM_TIMEOUT_SECONDS: float = 3.0
    DEFAULT_CIRCUITY_FACTOR: float = 1.35
    DEFAULT_AVERAGE_SPEED_KMH: float = 35.0
    DEFAULT_HANDLING_BUFFER_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
