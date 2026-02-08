from sqlalchemy.orm import Session
from app.db.models.ml_risk_log import MLRiskLog
from datetime import datetime, timedelta
import statistics

class ModelMonitor:
    def check_health(self, db: Session):
        """Checks for model staleness and variance."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        try:
            logs = db.query(MLRiskLog).filter(MLRiskLog.created_at >= cutoff).limit(20).all()

            if not logs:
                return {"status": "COLD", "message": "No recent predictions."}

            # Check for variance (frozen model detection)
            scores = [l.final_risk for l in logs if l.final_risk is not None]

            if len(scores) < 2:
                 # Not enough data to calculate variance, but we have some logs.
                 # We can consider it HEALTHY enough or COLD.
                 # Let's say HEALTHY but with a note if needed, or just return variance 0.
                 # Usually < 2 samples means we can't really judge variance well.
                 return {"status": "COLD", "message": "Insufficient data for variance check."}

            variance = statistics.stdev(scores)

            status = "HEALTHY" if variance > 0 else "FROZEN"

            message = f"Variance: {round(variance, 2)}"
            if status == "FROZEN":
                message = "Model outputs are static (frozen)."

            return {"status": status, "message": message}
        except Exception as e:
            return {"status": "WARNING", "message": "Model log inaccessible."}

model_monitor = ModelMonitor()
