import asyncio
import random
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.ml_risk_log import MLRiskLog
from app.db.models.analytics import RiskSnapshot
from app.services.mentor_engine import mentor_engine
from app.services.alert_engine import alert_engine
from app.services.benchmark_engine import benchmark_engine
from app.services.counterfactual_engine import counterfactual_engine
from app.services.social_harvester import social_harvester
from app.ml.risk_forecast_model import RiskForecastModel
from app.ml.lstm_risk_production import LSTMRiskProductionModel
from app.ml.feature_store import compute_features

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

    def __init__(self):
        self.market_high_demand_skills = [
            "Rust",
            "Go",
            "Python",
            "AI/ML",
            "React",
            "System Design",
            "Cloud Architecture",
            "TypeScript",
            "Kubernetes"
        ]

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
        skill_confidence = self._calculate_skill_confidence(raw_languages, linkedin_input)
        linkedin_skills = list(linkedin_input.get("skills", {}).keys())

        # -------------------------------
        # CAREER RISK ALERTS (CURRENT)
        # -------------------------------
        career_risks: List[Dict] = []
        hidden_gems: List[Dict] = []

        # 1. Low Confidence Alert
        for skill, confidence in skill_confidence.items():
            if confidence < 40:
                career_risks.append({
                    "level": "HIGH",
                    "skill": skill,
                    "message": f"Low confidence score in {skill}. Risk of interview rejection."
                })

        # 2. Imposter Syndrome Detector (LinkedIn Expert vs GitHub Empty)
        for skill in linkedin_skills:
            # Check if skill exists in raw_languages with sufficient bytes
            # Heuristic: < 10k bytes = "No Evidence"
            bytes_count = raw_languages.get(skill, raw_languages.get(skill.title(), 0))
            if bytes_count < 10_000:
                career_risks.append({
                    "level": "CRITICAL",
                    "skill": skill,
                    "message": f"IMPOSTER ALERT: You claim '{skill}' on LinkedIn but have <10k bytes of code."
                })

        # 3. Hidden Gem Detector (GitHub High vs LinkedIn Empty)
        for skill, bytes_count in raw_languages.items():
            if bytes_count > 50_000 and skill not in linkedin_skills:
                hidden_gems.append({
                    "type": "HIDDEN_GEM",
                    "skill": skill,
                    "message": f"You have {int(bytes_count/1000)}k bytes of {skill} code not listed on LinkedIn!"
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
        # (Contextual Benchmark: Company & Region segmentation)
        benchmark = benchmark_engine.compute(db, user)

        # -------------------------------
        # COUNTERFACTUAL ANALYSIS (WHAT-IF SCENARIOS)
        # -------------------------------
        # Recupera snapshots recentes para compor o histórico de features
        recent_snapshots = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.recorded_at.desc())
            .limit(5)
            .all()
        )
        
        # Computa features normalizadas para o modelo ML
        features = compute_features(metrics, recent_snapshots)

        # Adiciona avg_confidence explicitamente para SHAP analysis
        avg_confidence = sum(skill_confidence.values()) / max(len(skill_confidence), 1)
        features["avg_confidence"] = avg_confidence

        # Gera cenário contrafactual (ex: "Se você aumentar commits em 20%, o risco cai para X")
        counterfactual = counterfactual_engine.generate(
            features=features,
            current_risk=career_forecast["risk_score"]
        )

        # -------------------------------
        # MENTOR INTEGRATION
        # -------------------------------
        mentor_engine.proactive_from_counterfactual(
            db,
            user,
            counterfactual
        )

        # Generate the weekly plan from SHAP counterfactuals
        auto_weekly_plan = mentor_engine.generate_weekly_plan_from_shap(
            db,
            user,
            counterfactual
        )

        # -------------------------------
        # FINAL RESPONSE
        # -------------------------------
        return {
            "zone_a_holistic": {},
            "zone_b_matrix": skill_audit,
            "weekly_plan": weekly_plan,
            "auto_weekly_plan": auto_weekly_plan, # AI-generated plan
            "skill_confidence": skill_confidence,
            "career_risks": career_risks,
            "hidden_gems": hidden_gems,
            "career_forecast": career_forecast,
            "benchmark": benchmark,
            "counterfactual": counterfactual,
            "zone_a_radar": {},
            "missing_skills": []
        }

    # =========================================================
    # INDEPENDENT COUNTERFACTUAL ANALYSIS
    # =========================================================
    async def get_counterfactual(self, db: Session, user: User) -> Dict:
        """
        Gera uma análise contrafactual sob demanda (API isolada).
        Populates necessary data from user profile to run the model.
        """
        # 1. Recupera dados do perfil (Prefer live metrics, fallback to cached)
        metrics = await social_harvester.get_metrics(user)

        profile = user.career_profile
        raw_languages = metrics.get("languages", {}) # Use normalized key from get_metrics
        linkedin_input = profile.linkedin_alignment_data if profile else {}
        if not isinstance(linkedin_input, dict):
            linkedin_input = {}

        # 2. Calcula Skill Confidence
        skill_confidence = self._calculate_skill_confidence(raw_languages, linkedin_input)

        # 3. Calcula Risco Atual (Forecast)
        career_forecast = self.forecast_career_risk(
            db, user, skill_confidence, metrics
        )
        current_risk = career_forecast["risk_score"]

        # 4. Recupera Snapshots
        recent_snapshots = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.recorded_at.desc())
            .limit(5)
            .all()
        )

        # 5. Computa Features e Gera Counterfactual
        features = compute_features(metrics, recent_snapshots)

        # Adiciona avg_confidence explicitamente para SHAP analysis
        avg_confidence = sum(skill_confidence.values()) / max(len(skill_confidence), 1)
        features["avg_confidence"] = avg_confidence

        counterfactual = counterfactual_engine.generate(
            features=features,
            current_risk=current_risk
        )
        
        return counterfactual

    # =========================================================
    # HELPER: CALCULATE SKILL CONFIDENCE
    # =========================================================
    def _calculate_skill_confidence(
        self,
        raw_languages: Dict[str, int],
        linkedin_input: Dict
    ) -> Dict[str, int]:
        skill_confidence: Dict[str, int] = {}
        linkedin_skills = list(linkedin_input.get("skills", {}).keys())

        for skill, bytes_count in raw_languages.items():
            score = self.calculate_verified_score(
                skill, bytes_count, linkedin_skills
            )
            skill_confidence[skill] = int(score * 100)
        
        return skill_confidence

    # =========================================================
    # WEEKLY ROUTINE GENERATOR
    # =========================================================
    def _generate_weekly_routine(
        self,
        github_stats: Dict,
        user_streak: int
    ) -> Dict:
        raw_langs = github_stats.get("languages", {})

        # Select focus based on highest byte count, default to Python
        if raw_langs:
            focus = max(raw_langs, key=raw_langs.get)
        else:
            focus = "Python"

        return {
            "mode": "GROWTH",
            "focus": focus,
            "streak_bonus": user_streak >= 4,
            "tasks": [
                {
                    "day": "Mon",
                    "task": f"Refactor legacy code in {focus} to improve readability.",
                    "type": "Code"
                },
                {
                    "day": "Wed",
                    "task": f"Implement a new unit test suite for your {focus} projects.",
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
        profile = user.career_profile
        metrics = profile.github_activity_metrics if profile else {}
        commits_30d = metrics.get("commits_last_30_days", 0)
        market_score = profile.market_relevance_score if profile else 0

        # Priority 1: Stagnation
        if commits_30d < 5:
            summary = "High risk driven by low coding activity (stagnation)."
        # Priority 2: Market Relevance
        elif market_score < 50:
            summary = "Risk driven by low alignment with current market trends."
        # Priority 3: Default/Skill Gap
        else:
            summary = "Moderate risk due to specific skill gaps in your target role."

        return {
            "summary": summary,
            "factors": [
                {"factor": "Skill Gap", "impact": "High" if market_score < 50 else "Medium"},
                {"factor": "Commit Velocity", "impact": "High" if commits_30d < 5 else "Low"},
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
        profile = user.career_profile
        skills_snapshot = profile.skills_snapshot if profile and isinstance(profile.skills_snapshot, dict) else {}

        # Calculate base confidence bounded 0-100
        raw_confidence = skills_snapshot.get(skill, 0)
        base_confidence = int(raw_confidence)
        base_confidence = max(0, min(base_confidence, 100))

        growth = min(90, base_confidence + months * 7)

        market_trends = self.market_high_demand_skills

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
