from sqlalchemy.orm import Session
from statistics import mean, pstdev
from typing import Dict, Optional, List
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

class TeamHealthEngine:

    def team_burnout_risk(self, db: Session, user) -> Optional[Dict]:
        """Calculates Burnout Risk based on Stress + Variance"""
        profile = user.career_profile
        if not profile or not profile.team:
            return None

        # Query risk scores for the team
        # Limit to 50 latest snapshots to get a representative sample
        risks = (
            db.query(RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc()) # Consistent timestamp
            .limit(50)
            .all()
        )

        if not risks:
            return None

        scores = [r[0] for r in risks]

        if not scores:
            return None

        avg_risk = mean(scores)
        variance = pstdev(scores) if len(scores) > 1 else 0

        # heuristic: 60% average risk + 40% variance
        burnout_score = int((avg_risk * 0.6) + (variance * 0.4))
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

    def simulate_member_exit(self, db: Session, user) -> Optional[Dict]:
        """Simulates impact on Team Average Risk if the lowest-risk member (The Anchor) leaves."""
        profile = user.career_profile
        if not profile or not profile.team:
            return None

        # 1. Fetch raw data for the team (User ID + Risk Score)
        # Ordered by newest first to facilitate deduplication
        raw_data = (
            db.query(RiskSnapshot.user_id, RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc())
            .all()
        )

        if not raw_data:
            return None

        # 2. Deduplicate: Get only the latest score per user
        team_scores = {}
        for uid, score in raw_data:
            if uid not in team_scores:
                team_scores[uid] = score

        # Need at least 2 members to simulate an exit
        if len(team_scores) < 2:
            return None

        scores = list(team_scores.values())
        current_avg = mean(scores)

        # 3. Identify the "Anchor" (Member with LOWEST risk)
        anchor_score = min(scores)

        # 4. Simulate the team without the Anchor
        simulated_scores = [s for s in scores if s != anchor_score]

        # Handle edge case where multiple people have the same low score (remove only one instance)
        if len(simulated_scores) == len(scores):
             simulated_scores.remove(anchor_score)

        new_avg = mean(simulated_scores)
        impact = new_avg - current_avg

        return {
            "current_avg": int(current_avg),
            "new_avg_if_exit": int(new_avg),
            "impact": int(impact), # Positive means Risk INCREASED (Bad)
            "anchor_score": int(anchor_score)
        }

team_health_engine = TeamHealthEngine()
