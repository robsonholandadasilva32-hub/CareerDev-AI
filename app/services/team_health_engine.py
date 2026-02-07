from sqlalchemy.orm import Session
from statistics import mean, pstdev
from typing import Dict, Optional, List
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

class TeamHealthEngine:
    """
    Analyzes systemic risks within a team:
    1. Burnout (Variance)
    2. Bus Factor (Exit Simulation)
    3. Contribution Ranking (Positive Impact)
    """

    def team_burnout_risk(self, db: Session, user) -> Optional[Dict]:
        """Calculates Burnout Risk based on Stress + Variance"""
        profile = user.career_profile
        if not profile or not profile.team:
            return None

        # 1. Fetch recent risk scores for the team
        risks = (
            db.query(RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc())
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

        # Heuristic: High Avg Risk + High Variance = Burnout/Instability
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
        """Simulates impact if the lowest-risk member leaves (Bus Factor)"""
        profile = user.career_profile
        if not profile or not profile.team:
            return None

        raw_data = (
            db.query(RiskSnapshot.user_id, RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc())
            .all()
        )

        if not raw_data:
            return None

        # Deduplicate: Latest score per user
        team_scores = {}
        for uid, score in raw_data:
            if uid not in team_scores:
                team_scores[uid] = score

        if len(team_scores) < 2:
            return None

        scores = list(team_scores.values())
        current_avg = mean(scores)

        # Identify the "anchor" (lowest risk member)
        anchor_score = min(scores)

        # Simulate removal of the anchor
        simulated_scores = [s for s in scores if s != anchor_score]

        # Edge case: multiple members with same lowest score, remove only one instance?
        # The list comprehension removes ALL instances of that score.
        # Ideally we want to remove just one person.
        # Let's rebuild the list without one instance of anchor_score.

        simulated_scores = []
        removed = False
        for s in scores:
            if s == anchor_score and not removed:
                removed = True
                continue
            simulated_scores.append(s)

        new_avg = mean(simulated_scores) if simulated_scores else current_avg

        return {
            "current_avg": int(current_avg),
            "new_avg_if_exit": int(new_avg),
            "impact": int(new_avg - current_avg),
            "anchor_score": int(anchor_score)
        }

    def internal_health_ranking(self, db: Session, user) -> Optional[List[Dict]]:
        """
        Ranks team members by how much they lower (or raise) the team average.
        Positive Contribution = Stabilizer (Good).
        Negative Contribution = Risk Factor (Needs Support).
        """
        profile = user.career_profile
        if not profile or not profile.team:
            return None

        # 1. Fetch raw data (deduplication required)
        raw_data = (
            db.query(RiskSnapshot.user_id, RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.recorded_at.desc())
            .all()
        )

        if not raw_data:
            return None

        # 2. Deduplicate: Map UserID -> Latest Score
        latest_scores = {}
        for uid, score in raw_data:
            if uid not in latest_scores:
                latest_scores[uid] = score

        if not latest_scores:
            return None

        # 3. Calculate Baseline
        avg_team = mean(latest_scores.values())

        ranking = []

        # 4. Calculate Contribution (Delta)
        for uid, risk in latest_scores.items():
            # If Team Avg is 50 and My Risk is 20: 50 - 20 = +30 (I am helping by 30 points)
            # If Team Avg is 50 and My Risk is 80: 50 - 80 = -30 (I am hurting by 30 points)
            contribution = avg_team - risk

            ranking.append({
                "user_id": uid,
                "is_current_user": (uid == user.id),
                "risk": risk,
                "contribution": round(contribution, 1)
            })

        # 5. Sort by highest contribution (Stabilizers at top)
        ranking.sort(key=lambda x: x["contribution"], reverse=True)

        return ranking

# Singleton Instance
team_health_engine = TeamHealthEngine()
