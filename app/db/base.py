from app.db.base_class import Base

# Modelos Core
from app.db.models.user import User

# Modelos de Carreira
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.weekly_routine import WeeklyRoutine

# Modelos Auxiliares
from app.db.models.security import UserSession
from app.db.models.gamification import Badge, UserBadge
from app.db.models.audit import AuditLog
from app.db.models.skill_snapshot import SkillSnapshot
from app.db.models.mentor import MentorMemory
from app.db.models.analytics import RiskSnapshot
from app.db.models.governance import GovernanceLog
