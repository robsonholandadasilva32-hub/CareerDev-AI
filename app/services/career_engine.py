from typing import Dict, List


class CareerEngine:
    """
    Core service responsible for analyzing developer career signals
    and producing risk alerts, skill confidence, and weekly growth plans.
    """

    def analyze(
        self,
        raw_languages: Dict[str, int],
        linkedin_input: Dict,
        metrics: Dict,
        skill_audit: Dict
    ) -> Dict:
        # -------------------------------
        # SKILL CONFIDENCE SCORE
        # -------------------------------
        skill_confidence: Dict[str, int] = {}

        linkedin_skills = list(linkedin_input.get("skills", {}).keys())

        for skill, bytes_count in raw_languages.items():
            score = self.calculate_verified_score(
                skill=skill,
                bytes_count=bytes_count,
                linkedin_skills=linkedin_skills
            )
            skill_confidence[skill] = int(score * 100)

        # -------------------------------
        # CAREER RISK ALERTS
        # -------------------------------
        career_risks: List[Dict] = []

        for skill, confidence in skill_confidence.items():
            if confidence < 40:
                career_risks.append({
                    "level": "HIGH",
                    "skill": skill,
                    "message": f"Low confidence score in {skill}. Risk of interview rejection."
                })

        if metrics.get("commits_last_30_days", 0) < 5:
            career_risks.append({
                "level": "MEDIUM",
                "message": "Low coding activity detected. Skills may decay."
            })

        # -------------------------------
        # WEEKLY GROWTH PLAN
        # -------------------------------
        weekly_plan = self._generate_weekly_routine(
            github_stats=metrics,
            user_streak=metrics.get("streak", 0)
        )

        # -------------------------------
        # FINAL RESPONSE
        # -------------------------------
        return {
            "zone_a_holistic": {},          # placeholder
            "zone_b_matrix": skill_audit,
            "weekly_plan": weekly_plan,
            "skill_confidence": skill_confidence,
            "career_risks": career_risks,
            "zone_a_radar": {},             # placeholder
            "missing_skills": []            # placeholder
        }

    # ------------------------------------------------------------------
    # AUXILIARY: GENERATE WEEKLY ROUTINE
    # ------------------------------------------------------------------
    def _generate_weekly_routine(
        self,
        github_stats: Dict,
        user_streak: int
    ) -> Dict:
        raw_langs = github_stats.get("languages", {})

        python_score = raw_langs.get("Python", 0)
        rust_score = raw_langs.get("Rust", 0)

        focus = "Rust" if (python_score > 100_000 and rust_score < 5_000) else "Python"

        suggested_pr = {
            "repo": "rust-lang/rustlings",
            "title": f"Practice: {focus} CLI improvement",
            "description": "This PR improves CLI parsing as part of weekly growth plan.",
            "difficulty": "Easy"
        }

        return {
            "mode": "GROWTH",
            "focus": focus,
            "tasks": [
                {
                    "day": "Mon",
                    "task": f"Learn: {focus} fundamentals",
                    "type": "Learn"
                },
                {
                    "day": "Wed",
                    "task": f"Build a CLI tool in {focus}",
                    "type": "Code",
                    "action": "VERIFY_REPO",
                    "verify_keyword": focus.lower()
                }
            ],
            "suggested_pr": suggested_pr
        }

    # ------------------------------------------------------------------
    # PLACEHOLDER: VERIFIED SCORE CALCULATION
    # ------------------------------------------------------------------
    def calculate_verified_score(
        self,
        skill: str,
        bytes_count: int,
        linkedin_skills: List[str]
    ) -> float:
        """
        Dummy implementation.
        Replace with real scoring logic.
        """
        base = min(bytes_count / 100_000, 1.0)
        bonus = 0.2 if skill in linkedin_skills else 0.0
        return min(base + bonus, 1.0)

    career_engine = CareerEngine()
