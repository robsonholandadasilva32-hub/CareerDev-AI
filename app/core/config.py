from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "CareerDev AI"
    ENVIRONMENT: str = "development" # development, production, test
    ALLOWED_HOSTS: list[str] = ["*"]
    SECRET_KEY: str = "super-secret-key-change-in-production"
    SESSION_SECRET_KEY: str = "change-this-to-a-secure-random-string"

    # Database
    DATABASE_URL: str = "sqlite:///./careerdev.db"

    # 2FA / Notifications
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@careerdev.ai"
    ADMIN_EMAIL: str = "admin@careerdev-ai.online"

    # Advanced Email Settings
    SMTP_USE_TLS: bool = False # Implicit TLS (usually port 465)
    SMTP_USE_STARTTLS: bool = True # Explicit TLS (usually port 587)
    SMTP_TIMEOUT: int = 10 # Seconds

    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # AI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5-mini"

    # OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None

    # Payments (Stripe)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None

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
