# Importa a Base declarativa (geralmente definida em base_class.py ou similar)
from app.db.base_class import Base

# --- IMPORTAÇÃO DE TODOS OS MODELOS ---
# É crucial importar todos os modelos aqui para que o Alembic e o SQLAlchemy 
# consigam "enxergar" as tabelas e resolver os relacionamentos (ForeignKeys) 
# antes de iniciar o banco de dados.

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.security import UserSession
from app.db.models.gamification import Badge, UserBadge

# A CORREÇÃO: Importando o modelo que estava faltando
from app.db.models.weekly_routine import WeeklyRoutine
from app.db.models.audit import LoginHistory
