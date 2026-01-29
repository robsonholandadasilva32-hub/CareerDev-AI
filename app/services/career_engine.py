from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan, MLRiskLog
from app.services.mentor_engine import mentor_engine
from app.ml.risk_forecast_model import RiskForecastModel

# ---------------------------------------------------------
# ML FORECASTER (SINGLETON)
# ---------------------------------------------------------
ml_forecaster = RiskForecastModel()


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
        # SKILL CONFIDENCE SCORE
        # -------------------------------
        skill_confidence: Dict[str, int] = {}
        linkedin_skills = list(linkedin_input.get("skills", {}).keys())

        for skill, bytes_count in raw_languages.items():
            score = self.calculate_verified_score(
                skill, bytes_count, linkedin_skills
            )
            skill_confidence[skill] = int(score * 100)

        # -------------------------------
        # CAREER RISK ALERTS (CURRENT)
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
        # WEEKLY GROWTH PLAN
        # -------------------------------
        weekly_plan = self._generate_weekly_routine(
            github_stats=metrics,
            user_streak=user.streak_count or 0
        )

        # -------------------------------
        # ACCELERATOR MODE DECISION
        # -------------------------------
        if self.should_enable_accelerator(
            skill_confidence, career_risks, user.streak_count or 0
        ):
            weekly_plan["mode"] = "ACCELERATOR"

        # -------------------------------
        # CAREER RISK FORECAST (HYBRID)
        # -------------------------------
        # Atualizado para passar db e user para log de ML
        career_forecast = self.forecast_career_risk(
            db, user, skill_confidence, metrics
        )

        # -------------------------------
        # MENTOR PROACTIVE INSIGHTS
        # -------------------------------
        mentor_engine.proactive_insights(
            db,
            user,
            {
                "career_forecast": career_forecast,
                "weekly_plan": weekly_plan
            }
        )

        # -------------------------------
        # FINAL RESPONSE
        # -------------------------------
        return {
            "zone_a_holistic": {},
            "zone_b_matrix": skill_audit,
            "weekly_plan": weekly_plan,
            "skill_confidence": skill_confidence,
            "career_risks": career_risks,
            "career_forecast": career_forecast,
            "zone_a_radar": {},
            "missing_skills": []
        }

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
    # CAREER RISK FORECAST (HYBRID: RULES + ML + LOGGING)
    # =========================================================
    def forecast_career_risk(
        self,
        db: Session,
        user: User,
        skill_confidence: Dict[str, int],
        metrics: Dict
    ) -> Dict:
        risk_score = 0
        reasons: List[str] = []

        avg_conf = sum(skill_confidence.values()) / max(len(skill_confidence), 1)

        # --- Lógica Baseada em Regras ---
        if avg_conf < 60:
            risk_score += 30
            reasons.append("Overall skill confidence trending low.")

        commits_30d = metrics.get("commits_last_30_days", 0)
        if commits_30d < 10:
            risk_score += 30
            reasons.append("Low coding activity detected.")

        if metrics.get("velocity_score") == "Low":
            risk_score += 20
            reasons.append("Development velocity decreasing.")

        # --- Ajuste via ML e Persistência de Log ---
        try:
            # Predição com mais contexto
            ml_result = ml_forecaster.predict(avg_conf, commits_30d)
            
            # Persistência do Log
            new_log = MLRiskLog(
                user_id=user.id,
                ml_risk=ml_result["ml_risk"],
                rule_risk=risk_score,
                model_version=ml_result.get("model_version", "v1.0")
            )
            db.add(new_log)
            db.commit()

            # Cálculo Híbrido Final
            risk_score = int((risk_score + ml_result["ml_risk"]) / 2)
            
        except Exception as e:
            db.rollback() # Garante integridade da sessão em caso de erro no log
            # Em produção, idealmente logar o erro 'e' em um sistema de observabilidade
            pass

        # --- Classificação Final ---
        level = "LOW"
        summary = "Career trajectory stable."

        if risk_score >= 60:
            level = "HIGH"
            summary = "High probability of stagnation or rejection within 6 months."
        elif risk_score >= 30:
            level = "MEDIUM"
            summary = "Moderate career risk detected within next 6 months."

        return {
            "risk_level": level,
            "risk_score": risk_score,
            "summary": summary,
            "reasons": reasons
        }

    # =========================================================
    # RISK EXPLAINABILITY (XAI)
    # =========================================================
    def explain_risk(self, user: User) -> Dict:
        """
        Provides a human-readable explanation of risk factors.
        Currently hardcoded for demo/MVP purposes.
        """
        return {
            "summary": "Your risk is driven by low Rust exposure and declining commit velocity.",
            "factors": [
                {"factor": "Skill Gap", "impact": "High"},
                {"factor": "Commit Velocity", "impact": "Medium"},
                {"factor": "Market Demand", "impact": "High"}
            ]
        }

    # =========================================================
    # SKILL PATH SIMULATION (UNIFIED)
    # =========================================================
    def simulate_skill_path(
        self,
        user: User,
        skill: str,
        months: int = 6
    ) -> Dict:
        """
        Simulates expected skill growth over time.

        - Backward compatible (months optional)
        - Growth capped
        - Market alignment fail-safe
        """
        base_confidence = 40
        growth = min(90, base_confidence + months * 7)

        market_trends = getattr(self, "market_trends", [])

        return {
            "skill": skill,
            "months": months,
            "expected_confidence": growth,
            "market_alignment": (
                "High" if skill in market_trends else "Medium"
            ),
            "summary": (
                f"Learning {skill} for {months} months significantly improves career outlook."
            )
        }

    # =========================================================
    # WEEKLY HISTORY (ASYNC / DB-DRIVEN)
    # =========================================================
    async def get_weekly_history(
        self,
        db: Session,
        user: User
    ) -> List[Dict]:
        routines = (
            db.query(LearningPlan)
            .filter(LearningPlan.user_id == user.id)
            .order_by(LearningPlan.created_at.desc())
            .limit(12)
            .all()
        )

        return [
            {
                "week": r.week_id,
                "focus": r.focus,
                "completion": r.completion_rate,
                "mode": r.mode
            }
            for r in routines
        ]


# ---------------------------------------------------------
# SERVICE INSTANCE
# ---------------------------------------------------------
career_engine = CareerEngine()
