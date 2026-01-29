from app.db.base_class import Base

# Importar TODOS os modelos
from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.security import UserSession
from app.db.models.gamification import Badge, UserBadge
from app.db.models.weekly_routine import WeeklyRoutine

# Importar AuditLog
from app.db.models.audit import AuditLog
