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
