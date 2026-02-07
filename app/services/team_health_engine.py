from sqlalchemy.orm import Session
from statistics import mean, pstdev
from typing import Dict, Optional
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

class TeamHealthEngine:
    """
    Calculates Burnout Risk based on:
    1. High Average Risk (Systemic Stress)
    2. High Variance (Inequality/Isolation)
    """

    def team_burnout_risk(self, db: Session, user) -> Optional[Dict]:
        profile = user.career_profile
        if not profile or not profile.team:
            return None
        # Query recent snapshots for all team members
        # We join CareerProfile to ensure we only get peers from the same team
        risks = (
            db.query(RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.created_at.desc())
            .limit(50) # Limit to recent data sample
            .all()
        )
        if not risks:
            return None
        scores = [r[0] for r in risks]

        if not scores:
            return None
        avg_risk = mean(scores)
        # Population standard deviation (requires at least one data point, but meaningful with >1)
        variance = pstdev(scores) if len(scores) > 1 else 0
        # Heuristic Formula: 60% weight on raw risk, 40% on variance (instability)
        burnout_score = int((avg_risk * 0.6) + (variance * 0.4))

        # Cap at 100
        burnout_score = min(100, burnout_score)
        level = "LOW"
        if burnout_score >= 60:
            level = "HIGH"
        elif burnout_score >= 30:
            level = "MEDIUM"
        return {
            "burnout_score": burnout_score,
            "level": level,
            "avg_risk": int(avg_risk),
            "variance": int(variance)
        }

# Singleton Instance
team_health_engine = TeamHealthEngine()
