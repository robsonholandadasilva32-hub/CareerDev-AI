import logging
import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.mentor import MentorMemory
from app.db.models.user import User
from app.services.embedding_service import embed_text

logger = logging.getLogger(__name__)


class MentorEngine:
    """
    Motor responsável pela inteligência do Mentor IA.

    Responsabilidades:
    - Persistir memórias (curto e longo prazo)
    - Gerar insights proativos baseados em dados de carreira
    - Fornecer conselhos diários (placeholder para LLM)
    - Armazenar contexto relevante do usuário
    - Permitir recall semântico (embedding-based, sem quebrar o schema atual)
    """

    # -------------------------------------------------
    # CORE MEMORY STORAGE (COM EMBEDDING OPCIONAL)
    # -------------------------------------------------
    def store(
        self,
        db: Session,
        user: User,
        category: str,
        content: str,
        context_key: Optional[str] = None,
        with_embedding: bool = True
    ):
        """
        Persiste uma memória do mentor.

        O embedding é armazenado serializado dentro de `memory_value`
        para manter compatibilidade com o schema atual.
        """
        try:
            final_key = context_key if context_key else category

            payload = {
                "content": content,
                "category": category
            }

            if with_embedding:
                try:
                    payload["embedding"] = embed_text(content)
                except Exception as e:
                    logger.warning(f"[MentorMemory] embedding falhou: {e}")

            memory = MentorMemory(
                user_id=user.id,
                context_key=final_key,
                memory_value=json.dumps(payload)
            )

            db.add(memory)
            db.commit()

            logger.info(
                f"[MentorMemory] user={user.id} key={final_key} category={category}"
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
    ) -> List[str]:
        """
        Gera insights automáticos baseados nos dados de carreira.
        """
        insights: List[str] = []

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
    # COUNTERFACTUAL PROACTIVE INSIGHTS
    # -------------------------------------------------
    def proactive_from_counterfactual(self, db: Session, user: User, counterfactual: dict):
        # Safety checks
        if not counterfactual or not counterfactual.get("actions"):
            return

        # Extract top action safely
        top_action = counterfactual["actions"][0]
        action_name = top_action.get("action", "Unknown Action")
        impact_score = top_action.get("impact", "N/A")

        message = (
            f"🚀 Quick Win Detected: Focus on '{action_name}'. "
            f"Our simulation shows this could immediately lower your career risk factor "
            f"by {impact_score} points."
        )

        self.store(db, user, "PROACTIVE", message)

    # -------------------------------------------------
    # MULTI-WEEK PLANNING
    # -------------------------------------------------
    def generate_multi_week_plan(self, db: Session, user: User, counterfactual: dict):
        # Validation
        if not counterfactual or not counterfactual.get("actions"):
            return None
        weeks = []
        # Generate a 4-week progression
        for i in range(4):
            week_label = f"Week {i+1}"

            # In a future iteration, we can vary intensity per week.
            # For now, we emphasize consistency on the key actions.
            week_plan = {
                "week": week_label,
                "tasks": []
            }
            for action in counterfactual["actions"]:
                week_plan["tasks"].append({
                    "task": action["action"],
                    "expected_impact": action["impact"],
                    "status": "Pending" # Default state for UI
                })
            weeks.append(week_plan)
        # Log the generation event
        self.store(
            db,
            user,
            "MULTI_WEEK_PLAN",
            "Adaptive 4-week improvement roadmap generated."
        )
        return weeks

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
    # WELCOME MESSAGE
    # -------------------------------------------------
    def welcome_message(self, db: Session, user: User):
        """
        Registers the initial welcome interaction in the mentor's memory.
        """
        self.store(
            db,
            user,
            "WELCOME",
            "Welcome! Your career analysis is ready. I’ll step in only when it matters."
        )

    # -------------------------------------------------
    # CONTEXT MEMORY (SEM EMBEDDING)
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
                context_key=key,
                memory_value=json.dumps({
                    "content": value,
                    "category": "CONTEXT"
                })
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
    # SEMANTIC RECALL (RAG-READY)
    # -------------------------------------------------
    def recall_semantic(
        self,
        db: Session,
        user: User,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[str]:
        """
        Recupera memórias semanticamente próximas usando cosine-like similarity.
        """
        memories = (
            db.query(MentorMemory)
            .filter(MentorMemory.user_id == user.id)
            .all()
        )

        scored = []

        for m in memories:
            try:
                payload = json.loads(m.memory_value)
                emb = payload.get("embedding")
                content = payload.get("content")

                if not emb or not content:
                    continue

                # Cosine Similarity simplificado (assumindo vetores normalizados)
                score = sum(a * b for a, b in zip(emb, query_embedding))
                scored.append((score, content))

            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:limit]]


# -------------------------------------------------
# SINGLETON INSTANCE
# -------------------------------------------------
mentor_engine = MentorEngine()
