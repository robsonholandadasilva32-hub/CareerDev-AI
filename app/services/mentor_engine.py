import logging
from sqlalchemy.orm import Session

from app.db.models.mentor_memory import MentorMemory
from app.db.models.user import User

logger = logging.getLogger(__name__)


class MentorEngine:
    """
    Motor responsável pela inteligência do Mentor IA.

    Responsabilidades:
    - Persistir memórias (curto e longo prazo)
    - Gerar insights proativos baseados em dados de carreira
    - Fornecer conselhos diários (placeholder para LLM)
    - Armazenar contexto relevante do usuário
    """

    # -------------------------------------------------
    # CORE MEMORY STORAGE
    # -------------------------------------------------
    def store(
        self,
        db: Session,
        user: User,
        category: str,
        content: str,
        context_key: str | None = None
    ):
        """
        Persiste uma memória do mentor.
        """
        try:
            memory = MentorMemory(
                user_id=user.id,
                category=category,
                content=content,
                context_key=context_key
            )
            db.add(memory)
            db.commit()
            logger.info(
                f"[MentorMemory] user={user.id} category={category} content={content}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"[MentorMemory] erro ao salvar memória: {e}")

    # -------------------------------------------------
    # PROACTIVE INSIGHTS (DATA-DRIVEN)
    # -------------------------------------------------
    def proactive_insights(
        self,
        db: Session,
        user: User,
        career_data: dict
    ) -> list[str]:
        """
        Gera insights automáticos baseados nos dados de carreira.
        """
        insights: list[str] = []

        forecast = career_data.get("career_forecast", {})
        weekly_plan = career_data.get("weekly_plan", {})

        if forecast.get("risk_level") == "HIGH":
            insights.append(
                "⚠️ High career risk detected. Immediate skill execution recommended."
            )

        if weekly_plan.get("mode") == "ACCELERATOR":
            insights.append(
                "🚀 Accelerator Mode active. Focus on real PR delivery this week."
            )

        for msg in insights:
            self.store(
                db=db,
                user=user,
                category="PROACTIVE",
                content=msg
            )

        return insights

    # -------------------------------------------------
    # DAILY ADVICE (LLM PLACEHOLDER)
    # -------------------------------------------------
    def get_daily_advice(
        self,
        db: Session,
        user: User
    ) -> str:
        """
        Retorna um conselho simples.
        Futuro: gerar texto via LLM usando MentorMemory como contexto.
        """
        name = getattr(user, "full_name", None) or "Dev"
        advice = f"Olá {name}, continue focado no seu progresso diário!"

        self.store(
            db=db,
            user=user,
            category="ADVICE",
            content=advice
        )

        return advice

    # -------------------------------------------------
    # CONTEXT MEMORY
    # -------------------------------------------------
    def remember_context(
        self,
        db: Session,
        user: User,
        key: str,
        value: str
    ):
        """
        Salva contexto explícito do usuário (preferências, decisões, eventos).
        """
        try:
            memory = MentorMemory(
                user_id=user.id,
                category="CONTEXT",
                context_key=key,
                content=value
            )
            db.add(memory)
            db.commit()
            logger.info(
                f"[MentorContext] user={user.id} {key}={value}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"[MentorContext] erro ao salvar contexto: {e}")


# -------------------------------------------------
# SINGLETON INSTANCE
# -------------------------------------------------
mentor_engine = MentorEngine()
