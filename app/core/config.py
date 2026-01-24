from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "CareerDev AI"
    DOMAIN: str = "https://www.careerdev-ai.online"
    ENVIRONMENT: str = "development" # development, production, test
    ALLOWED_HOSTS: list[str] = ["*"]
    SECRET_KEY: str = "super-secret-key-change-in-production"
    SESSION_SECRET_KEY: str = "change-this-to-a-secure-random-string"

    # Database
    DATABASE_URL: str = "sqlite:///./careerdev.db"

    # Notification settings removed

    # AI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5-mini"
    OPENAI_FALLBACK_MODEL: str = "gpt-4o-mini"

    # OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None

    # Analytics (PostHog)
    POSTHOG_API_KEY: Optional[str] = None
    POSTHOG_HOST: str = "https://app.posthog.com"

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
