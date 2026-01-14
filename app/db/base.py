from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import models to register them with Base.metadata
from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.email_verification import EmailVerification
from app.db.models.otp import OTP
# from app.db.models.two_factory import TwoFactorMethod # Removing empty import for now
from app.db.models.gamification import Badge, UserBadge
from app.db.models.job import BackgroundJob
