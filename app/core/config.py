from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationInfo, model_validator
from typing import Optional, Any
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "CareerDev AI"
    RESUME_ANALYZER_TITLE: str = "Resume Analyzer"
    DOMAIN: str = "https://www.careerdev-ai.online"
    ENVIRONMENT: str = "development" # development, production, test
    ALLOWED_HOSTS: list[str] = ["*"]
    SECRET_KEY: str = "super-secret-key-change-in-production"
    SESSION_SECRET_KEY: str = "change-this-to-a-secure-random-string"

    # Database
    DATABASE_URL: str
    POSTGRES_URL: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def check_database_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("DATABASE_URL") and data.get("POSTGRES_URL"):
                print("DEBUG: Using POSTGRES_URL fallback for DATABASE_URL")
                data["DATABASE_URL"] = data.get("POSTGRES_URL")
        return data

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql://", 1)
        return v

    # Notification settings removed

    # AI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5-mini"
    LLM_MODEL_DISPLAY_NAME: str = "GPT-5-Mini"
    OPENAI_FALLBACK_MODEL: str = "gpt-4o-mini"

    # OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None

    # Analytics (PostHog)
    POSTHOG_API_KEY: Optional[str] = None
    POSTHOG_HOST: str = "https://app.posthog.com"

    # Monitoring (Sentry)
    SENTRY_DSN: Optional[str] = None

    # Feature Flags
    FEATURES: dict = {
        "ENABLE_CHATBOT": True,
        "ENABLE_VOICE_MODE": True,
        "ENABLE_SOCIAL_LOGIN": True,
        "ENABLE_REGISTRATION": True
    }

    class Config:
        env_file = ".env"
        extra = "ignore" # Prevent crash on extra env vars

settings = Settings()

if not settings.OPENAI_API_KEY:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.critical("OPENAI_API_KEY is missing. AI features will fail. Please check your environment variables.")
