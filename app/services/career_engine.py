import asyncio
import random
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.ml_risk_log import MLRiskLog
from app.db.models.analytics import RiskSnapshot 
from app.services.mentor_engine import mentor_engine
from app.services.alert_engine import alert_engine
from app.services.benchmark_engine import benchmark_engine # <--- Nova Importação
from app.ml.risk_forecast_model import RiskForecastModel
from app.ml.lstm_risk_production import LSTMRiskProductionModel

# ---------------------------------------------------------
# ML FORECASTERS (SINGLETONS)
# ---------------------------------------------------------
ml_forecaster = RiskForecastModel()
lstm_model = LSTMRiskProductionModel()


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
        # CAREER RISK FORECAST (HYBRID + LSTM + A/B TEST)
        # -------------------------------
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
        # BENCHMARK ENGINE
        # -------------------------------
        # Calcula a performance relativa do usuário vs. mercado
        benchmark = benchmark_engine.compute(db, user)

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
            "benchmark": benchmark, # <--- Adicionado ao retorno
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
    # RISK CLASSIFICATION HELPER
    # =========================================================
    def classify_risk_level(self, risk_score: int) -> str:
        """
        Maps a numeric risk score to a categorical level.
        Thresholds:
        - < 25: LOW
        - 25 to 59: MEDIUM
        - >= 60: HIGH
        """
        if risk_score < 25:
            return "LOW"
        if risk_score < 60:
            return "MEDIUM"
        return "HIGH"

    # =========================================================
    # CAREER RISK FORECAST (HYBRID: RULES + ML + LSTM + LOGGING)
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
        
        # Armazena o risco base (rule-based)
        rule_risk = risk_score

        # --- Ajuste via ML, LSTM e A/B Testing ---
        try:
            # 1. Predição Estática ML
            ml_result = ml_forecaster.predict(avg_conf, commits_30d)
            ml_risk = ml_result["ml_risk"]
            
            # Adiciona explicação do ML estático
            ml_explanation = self.explain_ml_forecast(
                ml_risk, 
                {"commits": commits_30d, "confidence": avg_conf}
            )
            reasons.append(ml_explanation)

            # 2. Lógica A/B Testing (Regras vs Híbrido Estático)
            experiment_group = "A" if random.random() < 0.5 else "B"

            if experiment_group == "A":
                final_risk = rule_risk
            else:
                final_risk = int((rule_risk + ml_risk) / 2)

            # 3. Refinamento Temporal via LSTM (Se houver histórico)
            try:
                recent_risks = [r.risk_score for r in db.query(RiskSnapshot)
                                .filter(RiskSnapshot.user_id == user.id)
                                .order_by(RiskSnapshot.recorded_at.desc())
                                .limit(10)
                                .all()][::-1]

                if len(recent_risks) == 10:
                    lstm_risk = lstm_model.predict(recent_risks)
                    # Média ponderada com o LSTM para suavizar a tendência
                    final_risk = int((final_risk + lstm_risk) / 2)
                    reasons.append(f"LSTM Temporal Analysis added context (Trend: {lstm_risk}%)")
            except Exception as lstm_err:
                pass

            # Persistência do Log Completo
            new_log = MLRiskLog(
                user_id=user.id,
                ml_risk=ml_risk,
                rule_risk=rule_risk,
                final_risk=final_risk,
                experiment_group=experiment_group,
                model_version=ml_result.get("model_version", "v1.0")
            )
            db.add(new_log)
            db.commit()

            # Atualiza o score final retornado
            risk_score = final_risk
            
        except Exception as e:
            db.rollback() 
            pass

        # --- Classificação Final ---
        level = self.classify_risk_level(risk_score)
        
        # --- Detecção de Mudança de Estado (Alert Engine) ---
        # Dispara alertas se o risco mudar significativamente (ex: LOW -> HIGH)
        alert_engine.detect_state_change(db, user, level)

        summary = "Career trajectory stable."
        if level == "HIGH":
            summary = "High probability of stagnation or rejection within 6 months."
        elif level == "MEDIUM":
            summary = "Moderate career risk detected within next 6 months."

        return {
            "risk_level": level,
            "risk_score": risk_score,
            "summary": summary,
            "reasons": reasons,
            "rule_risk": rule_risk,
            "ml_risk": ml_result.get("ml_risk", 0) if 'ml_result' in locals() else 0
        }

    # =========================================================
    # RISK EXPLAINABILITY (XAI) - STATIC
    # =========================================================
    def explain_risk(self, user: User) -> Dict:
        """
        Provides a human-readable explanation of risk factors.
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
    # RISK EXPLAINABILITY (XAI) - DYNAMIC ML
    # =========================================================
    def explain_ml_forecast(self, ml_risk, features):
        """
        Generates a dynamic explanation for the specific ML forecast.
        """
        return (
            f"The ML model predicts risk based on declining commit velocity "
            f"and skill confidence trends. Estimated risk: {ml_risk}%."
        )

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
    def _get_weekly_history_sync(
        self,
        db: Session,
        user_id: int
    ) -> List[Dict]:
        routines = (
            db.query(LearningPlan)
            .filter(LearningPlan.user_id == user_id)
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

    async def get_weekly_history(
        self,
        db: Session,
        user: User
    ) -> List[Dict]:
        """
        Asynchronously retrieves weekly learning history.
        Offloads the synchronous DB query to a thread to prevent blocking the event loop.
        """
        return await asyncio.to_thread(self._get_weekly_history_sync, db, user.id)


# ---------------------------------------------------------
# SERVICE INSTANCE
# ---------------------------------------------------------
career_engine = CareerEngine()
