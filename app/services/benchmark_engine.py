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
        
        # Percentile calculation: percent of peers with risk_score <= my score
        # Note: If risk is low (good), and I am low, I am "safer" than those with high risk.
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
        """
        Fetches the user's risk history for the longitudinal graph.
        Returns the last 12 snapshots in chronological order.
        """
        history = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.created_at.desc())  # Newest first
            .limit(12)
            .all()
        )

        if not history:
            return None

        # Reverse to chronological order (Oldest -> Newest) for display
        history = history[::-1]

        # Return Dictionary (Safer for Jinja2/JSON serialization than SimpleNamespace)
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