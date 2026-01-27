import httpx
import math
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan

class CareerEngine:
    def __init__(self):
        # In a real app, these would come from an external API or LLM analysis
        self.market_trends = {
            "Rust": "High",
            "Go": "Very High",
            "Python": "Stable",
            "Ethical AI": "Emerging"
        }

    def calculate_verified_score(self, skill: str, github_bytes: int, linkedin_claims: List[str]) -> float:
        """
        Formula: V_score = (GitHub_Weight * Volume_Factor) + (LinkedIn_Weight * Social_Proof)
        """
        GH_WEIGHT = 0.7  # Code proves ability
        LI_WEIGHT = 0.3  # Profile proves marketability

        # Normalize GitHub bytes (Logarithmic scale to avoid skew by massive repos)
        # log(1) = 0. log(22000) ~ 10. So /10 scales it nicely to 0-1.
        volume_factor = min(math.log(github_bytes + 1) / 10, 1.0) # Cap at 1.0

        # Check case-insensitive
        social_proof = 1.0 if skill.lower() in [s.lower() for s in linkedin_claims] else 0.0

        return (GH_WEIGHT * volume_factor) + (LI_WEIGHT * social_proof)

    def analyze_profile(self, db: Session, user: User) -> Dict:
        """
        Analyzes the user profile, fetching external data if available,
        and updates/creates the CareerProfile in the DB.
        """
        if not user:
            return {}

        profile = user.career_profile
        if not profile:
            profile = CareerProfile(user_id=user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # 1. Sync External Data (Simulation)
        if user.github_id and not profile.github_stats:
            # Simulate GitHub fetching
            # Real implementation would use: httpx.get(f"https://api.github.com/user/{user.github_id}")
            profile.github_stats = {
                "repos": 12,
                "top_languages": {"Python": 60, "JavaScript": 30, "Rust": 10},
                "last_commit": datetime.utcnow().isoformat()
            }
            # Update skills based on GH
            current_skills = profile.skills_snapshot or {}
            current_skills.update({"Rust": 20, "Python": 80}) # Mocked inference
            profile.skills_snapshot = current_skills
            db.commit()

        # 2. Return Structured Data
        return {
            "skills": profile.skills_snapshot or {"General": 10},
            "level": profile.experience_level,
            "focus": profile.target_role,
            "trends": self.market_trends
        }

    def generate_plan(self, db: Session, user: User) -> List[LearningPlan]:
        """
        Generates or retrieves the current learning plan.
        """
        # Check existing incomplete items
        existing_plan = db.query(LearningPlan).filter(
            LearningPlan.user_id == user.id,
            LearningPlan.status != "completed"
        ).all()

        if existing_plan:
            return existing_plan

        # Generate new items based on gaps
        new_items = []
        profile = user.career_profile
        skills = profile.skills_snapshot if profile else {}

        # Gaps Analysis (Heuristic)
        if skills.get("Rust", 0) < 30:
            new_items.append(LearningPlan(
                user_id=user.id,
                title="Fundamentos de Rust",
                description="Domine Ownership e Borrowing com o Rust Book.",
                technology="Rust",
                resources=["https://doc.rust-lang.org/book/"],
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        if skills.get("Go", 0) < 30:
             new_items.append(LearningPlan(
                user_id=user.id,
                title="Microsserviços com Go",
                description="Crie uma API RESTful usando Gin ou Echo.",
                technology="Go",
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        # Always add an AI Ethics item
        # Ensure user_id is passed explicitly from user.id
        new_items.append(LearningPlan(
            user_id=user.id,
            title="Introdução à IA Ética",
            description="Entenda os princípios de explicabilidade e viés algorítmico.",
            technology="AI Ethics",
            due_date=datetime.utcnow() + timedelta(days=14)
        ))

        db.add_all(new_items)
        db.commit()

        return new_items

    def get_career_dashboard_data(self, db: Session, user: User) -> Dict:
        """
        Returns the structured JSON object for the new Dashboard AI brain.
        Phase 3 Compliance: Strict JSON structure for HUD.
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)
        profile = user.career_profile

        # --- DATA PREP ---
        metrics = profile.github_activity_metrics or {}
        raw_languages = metrics.get("raw_languages", {})

        li_data = profile.linkedin_alignment_data or {}
        claimed_skills = li_data.get("claimed_skills", [])

        # ZONE A: HOLISTIC SCANNER (Professional Health Bar)
        # Logic: (Profile Completeness + GitHub Activity + Skill Verification Score) / 3
        # 1. Profile Completeness (Mock: Assume 80% if linkedin connected)
        p_completeness = 80 if li_data.get("connected") else 40

        # 2. GitHub Activity (Velocity)
        velocity_score = 85 if metrics.get("velocity_score") == "High" else 50

        # 3. Verified Skill Score (Average of Top 3 Skills)
        skill_ver_sum = 0
        top_skills = sorted(raw_languages.items(), key=lambda x: x[1], reverse=True)[:3]
        for skill, bytes_count in top_skills:
            skill_ver_sum += self.calculate_verified_score(skill, bytes_count, claimed_skills)

        avg_skill_ver = (skill_ver_sum / 3) * 100 if top_skills else 0

        holistic_score = int((p_completeness + velocity_score + avg_skill_ver) / 3)
        health_color = "green" if holistic_score > 80 else ("orange" if holistic_score > 50 else "red")

        # ZONE B: INTEREST VS REALITY MATRIX (Skill Audit)
        # Table: Skill | Detected in GitHub | Shown on LinkedIn | AI Verdict
        skill_audit = []
        all_skills = set(raw_languages.keys()) | set(claimed_skills)
        # Limit to top 5 relevant for display

        for skill in list(all_skills)[:6]:
            gh_bytes = raw_languages.get(skill, 0)
            in_gh = "✅ (Top Lang)" if gh_bytes > 5000 else ("⚠️ (In Progress)" if gh_bytes > 0 else "❌ (None)")

            in_li = "✅" if skill in claimed_skills else "❌"

            # AI Verdict Logic
            if in_gh.startswith("✅") and in_li == "✅":
                verdict = "Strong Asset"
            elif in_gh.startswith("⚠️") and in_li == "❌":
                verdict = "Hidden Gem (Add to CV)"
            elif in_gh.startswith("❌") and in_li == "✅":
                verdict = "Unverified (Build a Demo)"
            else:
                verdict = "Emerging Interest"

            skill_audit.append({
                "skill": skill,
                "github": in_gh,
                "linkedin": in_li,
                "verdict": verdict
            })

        # ZONE C: STRENGTHS & WEAKNESSES (AI Insight)
        # Use stored summary or fallback
        ai_insight_card = profile.ai_insights_summary or "System Analysis: Initializing Neural Link... Please wait for next scan."

        return {
            "zone_a_holistic": {
                "score": holistic_score,
                "color": health_color,
                "details": f"Profile: {p_completeness}% | Code Velocity: {metrics.get('velocity_score', 'N/A')}"
            },
            "zone_b_matrix": skill_audit,
            "zone_c_ai": {
                "insights": ai_insight_card
            },
            # Legacy/Secondary Data for Charts if needed
            "doughnut_data": profile.skills_graph_data
        }

career_engine = CareerEngine()
