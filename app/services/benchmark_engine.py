from sqlalchemy.orm import Session
from app.db.models.risk_snapshot import RiskSnapshot

class BenchmarkEngine:

    def compute(self, db: Session, user):
        user_risk = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.recorded_at.desc())
            .first()
        )

        if not user_risk:
            return None

        all_risks = (
            db.query(RiskSnapshot.risk_score)
            .order_by(RiskSnapshot.recorded_at.desc())
            .limit(1000)
            .all()
        )

        scores = sorted([r[0] for r in all_risks])
        percentile = int(
            sum(1 for s in scores if s <= user_risk.risk_score)
            / len(scores) * 100
        )

        return {
            "user_risk": user_risk.risk_score,
            "percentile": percentile,
            "message": f"You are safer than {percentile}% of developers on the platform."
        }

benchmark_engine = BenchmarkEngine()
