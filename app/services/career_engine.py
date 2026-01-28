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

    def analyze_skill_alignment(self, github_stats: Dict, linkedin_profile: Dict) -> List[Dict]:
        """
        Real Logic: Compares Code Volume (Reality) vs Profile Claims (Perception)
        """
        insights = []

        # Logic 1: The Imposter Detector
        for skill, bytes_count in github_stats.get('languages', {}).items():
            claimed_level = linkedin_profile.get('skills', {}).get(skill, 'None')

            # If High Claim on LinkedIn but < 1% code on GitHub
            if claimed_level == 'Expert' and bytes_count < 10000:
                insights.append({
                    "type": "CRITICAL",
                    "skill": skill,
                    "message": f"Discrepancy: You claim Expert in {skill} but show low code volume.",
                    "action": "GENERATE_MICRO_PROJECT"
                })

        # Logic 2: The Hidden Gem Detector
        # If High Code Volume on GitHub but NOT listed on LinkedIn
        for skill, bytes_count in github_stats.get('languages', {}).items():
            if skill not in linkedin_profile.get('skills', {}) and bytes_count > 50000:
                insights.append({
                    "type": "OPPORTUNITY",
                    "skill": skill,
                    "message": f"Hidden Gem: You have significant {skill} code. Add to LinkedIn immediately.",
                    "action": "UPDATE_PROFILE"
                })

        return insights

    def get_career_dashboard_data(self, db: Session, user: User) -> Dict:
        """
        Returns the structured JSON object for the new Dashboard AI brain.
        Now includes 'radar_data' and 'missing_skills'.
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)
        profile = user.career_profile

        # --- DATA PREP ---
        metrics = profile.github_activity_metrics or {}
        raw_languages = metrics.get("raw_languages", {})
        detected_frameworks = metrics.get("detected_frameworks", [])

        li_data = profile.linkedin_alignment_data or {}
        claimed_skills_list = li_data.get("claimed_skills", [])

        # Construct inputs for Real Logic
        # Assume 'Expert' for all claimed skills to satisfy the condition
        linkedin_profile_input = {"skills": {s: "Expert" for s in claimed_skills_list}}
        github_stats_input = {"languages": raw_languages}

        # ZONE A: HOLISTIC SCANNER (Professional Health Bar)
        # Logic: (Profile Completeness + GitHub Activity + Skill Verification Score) / 3
        p_completeness = 80 if li_data.get("connected") else 40
        velocity_score = 85 if metrics.get("velocity_score") == "High" else 50

        # Skill Verification
        skill_ver_sum = 0
        top_skills = sorted(raw_languages.items(), key=lambda x: x[1], reverse=True)[:3]
        for skill, bytes_count in top_skills:
            skill_ver_sum += self.calculate_verified_score(skill, bytes_count, claimed_skills_list)
        avg_skill_ver = (skill_ver_sum / 3) * 100 if top_skills else 0

        holistic_score = int((p_completeness + velocity_score + avg_skill_ver) / 3)
        health_color = "green" if holistic_score > 80 else ("orange" if holistic_score > 50 else "red")

        # ZONE B: CROSS-VERIFICATION ENGINE (REAL LOGIC)
        insights = self.analyze_skill_alignment(github_stats_input, linkedin_profile_input)

        # Transform insights to zone_b_matrix format
        skill_audit = []
        processed_skills = set()

        for insight in insights:
            processed_skills.add(insight["skill"])
            item = {
                "skill": insight["skill"],
                "verdict": "CRITICAL GAP" if insight["type"] == "CRITICAL" else "HIDDEN GEM",
                "color": "#ef4444" if insight["type"] == "CRITICAL" else "#10b981", # Red or Green
                "percentage": 10 if insight["type"] == "CRITICAL" else 90
            }
            skill_audit.append(item)

        # Add "MATCH" items (Verified Experts)
        # Logic: Claimed (Expert) AND High Code (> 10000)
        for skill in claimed_skills_list:
            if skill in raw_languages:
                bytes_count = raw_languages[skill]
                if bytes_count >= 10000 and skill not in processed_skills:
                    skill_audit.append({
                        "skill": skill,
                        "verdict": "MATCH",
                        "color": "#3b82f6", # Blue
                        "percentage": min(int(math.log(bytes_count + 1) * 8), 100) # Dynamic based on volume
                    })
                    processed_skills.add(skill)

        # Extract 'missing_skills' for Chatbot (Imposter Detected)
        missing_skills = [item['skill'] for item in skill_audit if item['verdict'] == 'CRITICAL GAP']

        # ZONE C: STRENGTHS & WEAKNESSES (AI Insight)
        ai_insight_card = profile.ai_insights_summary or "System Analysis: Initializing Neural Link... Please wait for next scan."

        # MARKET RADAR DATA
        # We map top 5 skills to 3 axes: Github (Reality), LinkedIn (Claims), Market (Demand)
        # Normalize to 1-100
        radar_labels = []
        d_github = []
        d_linkedin = []
        d_market = []

        # Use top 5 languages/frameworks from GitHub as base + any high market demand ones missing
        base_skills = list(raw_languages.keys())[:5]
        if not base_skills: base_skills = ["Python", "JavaScript", "Rust"]

        for skill in base_skills:
            radar_labels.append(skill)

            # GitHub Score (Log Volume)
            vol = raw_languages.get(skill, 0)
            d_github.append(min(int(math.log(vol + 1) * 8), 100))

            # LinkedIn Score (Binary-ish)
            d_linkedin.append(90 if skill in claimed_skills_list else 20)

            # Market Score (Lookup or Random High for Demo)
            market_val = 80
            if skill in self.market_trends:
                trend = self.market_trends[skill]
                market_val = 95 if trend == "Very High" else (85 if trend == "High" else 60)
            d_market.append(market_val)

        return {
            "zone_a_holistic": {
                "score": holistic_score,
                "color": health_color,
                "details": f"Profile: {p_completeness}% | Code Velocity: {metrics.get('velocity_score', 'N/A')}"
            },
            "zone_b_matrix": skill_audit,
            "zone_c_ticker": {
                "user_score": holistic_score
            },
            "zone_a_reality": {
                 "labels": radar_labels,
                 "values": d_github
            },
            "missing_skills": missing_skills,
            "doughnut_data": profile.skills_graph_data,
            "weekly_plan": profile.active_weekly_plan # For Growth Engine UI
        }

career_engine = CareerEngine()
