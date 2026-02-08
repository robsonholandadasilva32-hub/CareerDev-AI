from sqlalchemy.orm import Session
from statistics import mean, pstdev
from typing import Dict, Optional, List
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

class TeamHealthEngine:
    """
    Calculates Burnout Risk based on:
    1. High Average Risk (Systemic Stress)
    2. High Variance (Inequality/Isolation)
    And simulates the impact of key member exits.
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
            .limit(50)  # Limit to recent data sample
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

    def simulate_member_exit(self, db: Session, user) -> Optional[Dict]:
        """
        Simulates the impact on Team Average Risk if the lowest-risk member (The Anchor) leaves.
        """
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
        # Removing them usually causes the average risk to spike up.
        anchor_score = min(scores)

        # 4. Simulate the team without the Anchor
        # We use remove() on a copy to ensure we only remove one instance, even if multiple
        # members share the same lowest score (handling the duplicate anchor edge case correctly).
        scores_copy = list(scores)
        scores_copy.remove(anchor_score)
        simulated_scores = scores_copy

        new_avg = mean(simulated_scores)
        impact = new_avg - current_avg

        return {
            "current_avg": int(current_avg),
            "new_avg_if_exit": int(new_avg),
            "impact": int(impact), # Positive means Risk INCREASED (Bad)
            "anchor_score": int(anchor_score)
        }

    def internal_health_ranking(self, db: Session, user) -> List[Dict]:
        """
        Ranks team members by risk score and calculates their contribution to the team average.
        """
        profile = user.career_profile
        if not profile or not profile.team:
            return []

        # 1. Fetch raw data
        raw_data = (
            db.query(RiskSnapshot.user_id, RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc())
            .all()
        )

        if not raw_data:
            return []

        # 2. Deduplicate
        team_scores = {}
        for uid, score in raw_data:
            if uid not in team_scores:
                team_scores[uid] = score

        scores = list(team_scores.values())
        if not scores:
            return []

        team_avg = mean(scores)

        ranking = []
        for uid, score in team_scores.items():
            contribution = score - team_avg
            ranking.append({
                "user_id": uid,
                "is_current_user": (uid == user.id),
                "risk": score,
                "contribution": round(contribution, 1)
            })

        # Sort by risk ascending (lowest risk = rank 1)
        ranking.sort(key=lambda x: x["risk"])

        return ranking

    def simulate_new_hire(self, db: Session, user, hypothetical_risk: int = 20) -> Optional[Dict]:
        """
        Simulates the impact on Team Average Risk if a new Low-Risk Developer joins.
        Hypothetical Risk defaults to 20 (a stable senior dev).
        """
        profile = user.career_profile
        if not profile or not profile.team:
            return None
        # 1. Fetch raw data
        raw_data = (
            db.query(RiskSnapshot.user_id, RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc())
            .all()
        )
        if not raw_data: return None
        # 2. Deduplicate
        team_scores = {}
        for uid, score in raw_data:
            if uid not in team_scores:
                team_scores[uid] = score
        scores = list(team_scores.values())
        current_avg = mean(scores)
        # 3. Simulate Hire
        # Add the hypothetical new hire to the list
        scores.append(hypothetical_risk)
        new_avg = mean(scores)

        # Impact is usually negative (Risk decreases), so we invert for clarity if needed
        # Here: Negative impact means Risk went DOWN (Good)
        impact = new_avg - current_avg
        return {
            "current_avg": int(current_avg),
            "new_avg_with_hire": int(new_avg),
            "impact": int(impact),
            "hypothetical_risk": hypothetical_risk
        }

# Singleton Instance
team_health_engine = TeamHealthEngine()
