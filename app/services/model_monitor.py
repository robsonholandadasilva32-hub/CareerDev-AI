from statistics import mean, stdev
from app.db.models.ml_risk_log import MLRiskLog
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

class ModelMonitor:
    def check_health(self, db: Session):
        """
        Checks if ML models are producing varied, sane outputs.
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent_logs = db.query(MLRiskLog).filter(MLRiskLog.created_at >= cutoff).all()

            if not recent_logs:
                return {"status": "COLD_START", "score": 100, "message": "No data yet."}

            scores = [log.final_risk for log in recent_logs if log.final_risk is not None]

            if not scores:
                 return {"status": "COLD_START", "score": 100, "message": "No valid scores yet."}

            # Metric 1: Variance Check (Is the model stuck returning the same number?)
            variance = stdev(scores) if len(scores) > 1 else 0
            if variance < 2.0 and len(scores) > 5:
                return {"status": "FROZEN", "score": 20, "message": "Model outputs are static (High Drift Risk)."}

            # Metric 2: Bounds Check
            out_of_bounds = any(s < 0 or s > 100 for s in scores)
            if out_of_bounds:
                return {"status": "CRITICAL", "score": 0, "message": "Model producing invalid values."}

            return {
                "status": "HEALTHY",
                "score": 95,
                "message": f"Model active. Variance: {round(variance, 2)}. Samples: {len(scores)}"
            }
        except Exception as e:
            return {"status": "ERROR", "score": 0, "message": f"Monitor failure: {str(e)}"}

model_monitor = ModelMonitor()
