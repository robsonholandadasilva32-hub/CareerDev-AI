from app.db.models.analytics import RiskSnapshot
from app.services.mentor_engine import mentor_engine

class AlertEngine:

    def detect_state_change(self, db, user, new_level: str):
        last = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.recorded_at.desc())
            .first()
        )

        if last and last.risk_level != new_level:
            mentor_engine.store(
                db,
                user,
                "ALERT",
                f"Career risk changed from {last.risk_level} to {new_level}."
            )
            return True

        return False

alert_engine = AlertEngine()
