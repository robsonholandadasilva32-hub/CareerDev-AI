from app.db.declarative import Base

# Import models to register them with Base.metadata
from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
# EmailVerification removed
# OTP removed
# TwoFactorMethod removed
from app.db.models.gamification import Badge, UserBadge
# BackgroundJob removed
from app.db.models.security import AuditLog, UserSession
from app.db.models.audit import LoginHistory
