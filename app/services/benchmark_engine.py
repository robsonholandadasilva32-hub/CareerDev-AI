from sqlalchemy.orm import Session
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

class BenchmarkEngine:
    def compute(self, db: Session, user):
        profile = user.career_profile
        if not profile:
            return None

        latest = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.created_at.desc())
            .first()
        )
        if not latest:
            return None

        query = (
            db.query(RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
        )

        context = []
        if profile.company:
            query = query.filter(CareerProfile.company == profile.company)
            context.append(profile.company)
        if profile.region:
            query = query.filter(CareerProfile.region == profile.region)
            context.append(profile.region)

        peers = query.all()
        if not peers:
            return None

        scores = sorted([p[0] for p in peers])
        
        # Percentile: percent of peers with risk_score <= my score
        # Note: logic provided was: sum(1 for s in scores if s <= latest.risk_score) / len(scores) * 100
        # If risk_score 0 is "good" and 100 is "bad", then being <= my score means "safer or same safety"?
        # Wait. "you are safer than {percentile}% of them."
        # If my risk is 20 (Low). Peer is 80 (High). 20 <= 20. 80 is not <= 20.
        # So sum(s <= 20) would be small if everyone else is high risk.
        # Then percentile is small. "You are safer than 10% of them".
        # This seems inverted if "safer" means "better".
        # Usually "safer than X%" means I am in the top X% of safety.
        # If I have low risk, I am safer than people with high risk.
        # So I should be counting people with risk >= my risk?
        # But I must follow the provided logic:
        # "percentile = int(sum(1 for s in scores if s <= latest.risk_score) / len(scores) * 100)"
        # "you are safer than {percentile}% of them."

        # Let's re-read the provided snippet carefully.
        # "scores = sorted([p[0] for p in peers])"
        # "percentile = int(sum(1 for s in scores if s <= latest.risk_score) / len(scores) * 100)"

        # If risk score: 0 (safe) -> 100 (risky).
        # Me: 10. Peer1: 5, Peer2: 90.
        # Scores: [5, 10, 90].
        # s <= 10: 5, 10. Count = 2.
        # Percentile = 2/3 = 66%.
        # "You are safer than 66% of them."
        # Who am I safer than? I am safer than the guy with 90.
        # But I am NOT safer than the guy with 5.
        # So I am safer than 1 person (the 90 guy).
        # But the calculation counts 2 people (me and the 5 guy).
        # This implies "safer or as safe as"?
        # If I strictly follow the code provided, I implement the code provided.
        # The prompt said: "Implement this specific comparison logic: ... Execute the implementation exactly based on the specifications below."
        # So I will copy the logic exactly, even if I have doubts about the phrasing "safer than".

        percentile = int(
            sum(1 for s in scores if s <= latest.risk_score) / len(scores) * 100
        )
        
        return {
            "context": " / ".join(context),
            "percentile": percentile,
            "message": (
                f"Compared to developers in {', '.join(context)}, "
                f"you are safer than {percentile}% of them."
            )
        }

    def get_user_history(self, db: Session, user):
        # Fetch user's personal history (last 12 snapshots)
        # We fetch in descending order to get the most recent ones, then sort back to ascending for the chart
        recent_history = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.created_at.desc())
            .limit(12)
            .all()
        )

        if not recent_history:
            return None

        # Restore chronological order for the chart
        history = sorted(recent_history, key=lambda h: h.created_at)

        # Return separate arrays for Chart.js
        return {
            "labels": [h.created_at.strftime("%d/%m") for h in history],
            "values": [h.risk_score for h in history]
        }

    def compute_team_health(self, db, user):
        profile = user.career_profile
        if not profile or not profile.team:
            return None
        # 1. Fetch all snapshots for team members, ordered by newest first
        # We join CareerProfile to filter by team
        raw_data = (
            db.query(RiskSnapshot.user_id, RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.team == profile.team)
            .order_by(RiskSnapshot.created_at.desc())
            .all()
        )
        if not raw_data:
            return None
        # 2. Deduplicate: Keep only the latest score per user
        latest_scores = {}
        for user_id, score in raw_data:
            if user_id not in latest_scores:
                latest_scores[user_id] = score
        if not latest_scores:
            return None
        # 3. Calculate Average Risk of the Team
        avg_risk = sum(latest_scores.values()) / len(latest_scores)

        # 4. Invert to get "Health" (High Health = Low Risk)
        health_score = 100 - avg_risk
        return {
            "health_score": int(health_score),
            "label": "Strong" if health_score > 75 else "Stable" if health_score > 50 else "Critical",
            "member_count": len(latest_scores)
        }

benchmark_engine = BenchmarkEngine()
