# -------------------------------
# SKILL CONFIDENCE SCORE
# -------------------------------
skill_confidence = {}

for skill, bytes_count in raw_languages.items():
    score = self.calculate_verified_score(
        skill,
        bytes_count,
        list(linkedin_input["skills"].keys())
    )
    skill_confidence[skill] = int(score * 100)
# -------------------------------
# CAREER RISK ALERTS
# -------------------------------
career_risks = []

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
return {
    "zone_a_holistic": {...},
    "zone_b_matrix": skill_audit,
    "weekly_plan": weekly_plan,
    "skill_confidence": skill_confidence,
    "career_risks": career_risks,
    "zone_a_radar": {...},
    "missing_skills": [...]
}
# -------------------------------
# GENERATE WEKLY ROUTINE
# -------------------------------
def _generate_weekly_routine(self, github_stats: Dict, user_streak: int) -> Dict:
    raw_langs = github_stats.get('languages', {})
    python_score = raw_langs.get('Python', 0)
    rust_score = raw_langs.get('Rust', 0)

    focus = "Rust" if (python_score > 100000 and rust_score < 5000) else "Python"

    suggested_pr = {
        "repo": "rust-lang/rustlings",
        "title": f"Practice: {focus} CLI improvement",
        "description": f"This PR improves CLI parsing as part of weekly growth plan.",
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
