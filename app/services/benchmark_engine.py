from sqlalchemy.orm import Session
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

class BenchmarkEngine:
    def compute(self, db: Session, user):
        """
        Computes the Contextual Benchmark (Company & Region).
        """
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
        
        # Percentile calculation
        # Logic: Percent of peers with risk_score <= my score
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

    def compute_team_org(self, db: Session, user):
        """
        Computes the user's standing within their specific Team and Organization.
        Used for the 'Team Benchmark' panel.
        """
        profile = user.career_profile
        if not profile:
            return None
            
        # 1. Get user's latest snapshot
        latest = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.created_at.desc())
            .first()
        )
        if not latest:
            return None
            
        # 2. Base Query for Peers
        query = (
            db.query(RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
        )
        
        context = []
        has_filter = False
        
        # 3. Apply Hierarchical Filters
        if profile.organization:
            query = query.filter(CareerProfile.organization == profile.organization)
            context.append(profile.organization)
            has_filter = True
            
        if profile.team:
            query = query.filter(CareerProfile.team == profile.team)
            context.append(profile.team)
            has_filter = True
            
        # Optimization: Don't run query if user belongs to no team/org
        if not has_filter:
            return None
            
        peers = query.all()
        if not peers:
            return None
            
        # 4. Calculate Percentile
        scores = sorted([p[0] for p in peers])
        
        # Handle edge case: single user (100th percentile)
        if len(scores) == 1:
             percentile = 100
        else:
             percentile = int(
                 sum(1 for s in scores if s <= latest.risk_score) / len(scores) * 100
             )
             
        return {
            "context": " / ".join(context),
            "percentile": percentile,
            "message": (
                f"Within {', '.join(context)}, "
                f"you are safer than {percentile}% of your peers."
            )
        }

    def get_user_history(self, db: Session, user):
        """
        Fetch user's personal history (last 12 snapshots) for timeline charts.
        """
        # We fetch in descending order to get the most recent ones, then sort back to ascending
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
        # FIXED: Using 'data_points' instead of 'values' to avoid Jinja2 serialization issues
        return {
            "labels": [h.created_at.strftime("%d/%m") for h in history],
            "data_points": [h.risk_score for h in history] 
        }

    def compute_team_health(self, db, user):
        """
        Calculates the aggregate health of the user's team.
        """
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
