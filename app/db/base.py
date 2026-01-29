from app.db.base_class import Base

# Modelos Core
from app.db.models.user import User

# Modelos de Carreira
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.weekly_routine import WeeklyRoutine
from app.db.models.skill_snapshot import SkillSnapshot

# Modelos de Segurança e Gamificação
from app.db.models.security import UserSession
from app.db.models.gamification import Badge, UserBadge
from app.db.models.audit import AuditLog
