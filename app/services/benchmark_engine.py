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

    def compute_team_org(self, db: Session, user):
        profile = user.career_profile
        if not profile:
            return None
        # 1. Get user's latest snapshot
        latest = (
            db.query(RiskSnapshot) # <--- Using existing model
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

benchmark_engine = BenchmarkEngine()
