import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.skill_snapshot import SkillSnapshot
from app.db.models.risk_snapshot import RiskSnapshot
from app.services.mentor_engine import mentor_engine

# Tenta importar o modelo de ML, usa Mock se falhar para não quebrar o servidor
try:
    from app.ml.risk_forecast_model import RiskForecastModel
    ml_forecaster = RiskForecastModel()
except ImportError:
    class MockForecaster:
        def predict(self, val): return 0
    ml_forecaster = MockForecaster()

logger = logging.getLogger(__name__)

class CareerEngine:
    """
    Core service responsible for analyzing developer career signals
    and producing risk alerts, growth plans,
    forecasts and mentor-driven insights.
    """

    # =========================================================
    # MAIN ANALYSIS PIPELINE
    # =========================================================
    def analyze(
        self,
        db: Session,
        raw_languages: Dict[str, int],
        linkedin_input: Dict,
        metrics: Dict,
        skill_audit: Dict,
        user: User
    ) -> Dict:
        # -------------------------------
        # 1. SKILL CONFIDENCE SCORE
        # -------------------------------
        skill_confidence: Dict[str, int] = {}
        linkedin_skills = list(linkedin_input.get("skills", {}).keys())

        for skill, bytes_count in raw_languages.items():
            score = self.calculate_verified_score(
                skill, bytes_count, linkedin_skills
            )
            skill_confidence[skill] = int(score * 100)

        # -------------------------------
        # 2. CAREER RISK ALERTS (CURRENT)
        # -------------------------------
        career_risks: List[Dict] = []

        for skill, confidence in skill_confidence.items():
            if confidence < 40:
                career_risks.append({
                    "level": "HIGH",
                    "skill": skill,
                    "message": f"Low confidence score in {skill}. Risk of interview rejection."
                })

        if metrics.get("commits_last_30_days", 0) < 5:
            career_risks.append({
                "level": "MEDIUM",
                "message": "Low coding activity detected. Skills may decay."
            })

        # -------------------------------
        # 3. WEEKLY GROWTH PLAN
        # -------------------------------
        weekly_plan = self._generate_weekly_routine(
            github_stats=metrics,
            user_streak=user.streak_count or 0
        )

        # -------------------------------
        # 4. ACCELERATOR MODE DECISION
        # -------------------------------
        if self.should_enable_accelerator(
            skill_confidence, career_risks, user.streak_count or 0
        ):
            weekly_plan["mode"] = "ACCELERATOR"

        # -------------------------------
        # 5. CAREER RISK FORECAST (6 MONTHS)
        # -------------------------------
        career_forecast = self.forecast_career_risk(
            skill_confidence, metrics
        )

        # -------------------------------
        # 6. PERSISTENCE (Saving to DB)
        # -------------------------------
        # Isso garante que as tabelas que corrigimos (Risk/Skill Snapshots) sejam populadas
        self._persist_data(db, user, skill_confidence, career_forecast)

        # -------------------------------
        # 7. MENTOR PROACTIVE INSIGHTS
        # -------------------------------
        mentor_insights = mentor_engine.proactive_insights(
            db,
            user,
            {
                "career_forecast": career_forecast,
                "weekly_plan": weekly_plan
            }
        )

        # -------------------------------
        # 8. FINAL RESPONSE
        # -------------------------------
        return {
            "zone_a_holistic": {},
            "zone_b_matrix": skill_audit,
            "weekly_plan": weekly_plan,
            "skill_confidence": skill_confidence,
            "career_risks": career_risks,
            "career_forecast": career_forecast,
            "zone_a_radar": {},
            "missing_skills": [],
            "mentor_insights": mentor_insights
        }

    # =========================================================
    # PERSISTENCE HELPER
    # =========================================================
    def _persist_data(self, db: Session, user: User, skills: Dict, forecast: Dict):
        """
        Salva os dados calculados no banco de dados para histórico.
        """
        try:
            # Salvar Skills
            for skill, score in skills.items():
                # Verifica se já salvou hoje para não duplicar
                exists = db.query(SkillSnapshot).filter(
                    SkillSnapshot.user_id == user.id,
                    SkillSnapshot.skill == skill,
                    # Lógica simplificada de data, idealmente filtrar por dia
                ).order_by(SkillSnapshot.recorded_at.desc()).first()
                
                # Se não existe ou é antigo, salva novo
                if not exists:
                    db.add(SkillSnapshot(user_id=user.id, skill=skill, confidence_score=score))

            # Salvar Risco (Se for Alto ou Médio)
            if forecast.get("risk_score", 0) > 30:
                # Evita spam de riscos iguais
                exists_risk = db.query(RiskSnapshot).filter(
                    RiskSnapshot.user_id == user.id,
                    RiskSnapshot.risk_factor == "General Forecast"
                ).order_by(RiskSnapshot.created_at.desc()).first()

                if not exists_risk:
                    db.add(RiskSnapshot(
                        user_id=user.id,
                        risk_factor="General Forecast",
                        risk_score=forecast["risk_score"],
                        mitigation_strategy=forecast["summary"]
                    ))

            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist career data: {e}")
            db.rollback()

    # =========================================================
    # WEEKLY ROUTINE GENERATOR
    # =========================================================
    def _generate_weekly_routine(
        self,
        github_stats: Dict,
        user_streak: int
    ) -> Dict:
        raw_langs = github_stats.get("languages", {})
        python_score = raw_langs.get("Python", 0)
        rust_score = raw_langs.get("Rust", 0)

        focus = "Rust" if python_score > 100_000 and rust_score < 5_000 else "Python"

        return {
            "mode": "GROWTH",
            "focus": focus,
            "streak_bonus": user_streak >= 4,
            "tasks": [
                {
                    "day": "Mon",
                    "task": f"Learn: {focus} fundamentals",
                    "type": "Learn"
                },
                {
                    "day": "Wed",
                    "task": f"Build a CLI tool in {focus}",
                    "type": "Code",
                    "action": "VERIFY_REPO",
                    "verify_keyword": focus.lower()
                }
            ]
        }

    # =========================================================
    # ACCELERATOR DECISION ENGINE
    # =========================================================
    def should_enable_accelerator(
        self,
        skill_confidence: Dict[str, int],
        career_risks: List[Dict],
        streak: int
    ) -> bool:
        avg = sum(skill_confidence.values()) / max(len(skill_confidence), 1)
        return avg >= 80 and streak >= 4 and not any(
            r["level"] == "HIGH" for r in career_risks
        )

    # =========================================================
    # VERIFIED SCORE CALCULATION
    # =========================================================
    def calculate_verified_score(
        self,
        skill: str,
        bytes_count: int,
        linkedin_skills: List[str]
    ) -> float:
        base = min(bytes_count / 100_000, 1.0)
        bonus = 0.2 if skill in linkedin_skills else 0.0
        return min(base + bonus, 1.0)

    # =========================================================
    # CAREER RISK FORECAST (HYBRID: RULES + ML)
    # =========================================================
    def forecast_career_risk(
        self,
        skill_confidence: Dict[str, int],
        metrics: Dict
    ) -> Dict:
        risk_score = 0
        reasons: List[str] = []

        avg_conf = sum(skill_confidence.values()) / max(len(skill_confidence), 1)

        if avg_conf < 60:
            risk_score += 30
            reasons.append("Overall skill confidence trending low.")

        if metrics.get("commits_last_30_days", 0) < 10:
            risk_score += 30
            reasons.append("Low coding activity detected.")

        if metrics.get("velocity_score") == "Low":
            risk_score += 20
            reasons.append("Development velocity decreasing.")

        # -------------------------------
        # ML RISK ADJUSTMENT (FAIL-SAFE)
        # -------------------------------
        try:
            ml_risk = ml_forecaster.predict(avg_conf)
            risk_score = int((risk_score + ml_risk) / 2)
        except Exception:
            pass

        # -------------------------------
        # FINAL CLASSIFICATION
        # -------------------------------
        level = "LOW"
        summary = "Career trajectory stable."

        if risk_score >= 60:
            level = "HIGH"
            summary = "High probability of stagnation or rejection within 6 months."
        elif risk_score >= 30:
            level = "MEDIUM"
            summary = "Moderate career risk detected within next
