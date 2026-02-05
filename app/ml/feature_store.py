# app/ml/feature_store.py

# List of high-demand skills for market gap analysis
MARKET_TRENDS = [
    "Rust",
    "Python",
    "Go",
    "TypeScript",
    "Kubernetes",
    "React",
    "AWS",
    "System Design"
]

def compute_features(metrics, snapshots):
    """
    Computes normalized features for ML models and Counterfactual Analysis.

    Args:
        metrics (dict): GitHub activity metrics (e.g. commits, languages).
        snapshots (list): List of RiskSnapshot objects, ordered by date DESC.

    Returns:
        dict: Feature vector matching CounterfactualEngine expectations.
    """
    # Defensive programming: Ensure metrics is a dict to prevent crashes
    if not isinstance(metrics, dict):
        metrics = {}

    # 1. Commit Velocity
    # Maps 'commits_last_30_days' to 'commit_velocity'
    commit_velocity = metrics.get("commits_last_30_days", 0)

    # 2. Skill Slope (Proxy: Risk Delta)
    # We use Risk Score to proxy skill confidence trend.
    # Logic: If Risk decreases (Old > New), Slope is Positive (Good).
    #        If Risk increases (Old < New), Slope is Negative (Bad).
    skill_slope = 0
    if snapshots and len(snapshots) > 0:
        # Assuming snapshots are ordered DESC (0 is Newest, -1 is Oldest)
        newest = snapshots[0]
        oldest = snapshots[-1]

        # Use getattr to prevent AttributeError if risk_score is missing
        new_risk = getattr(newest, "risk_score", 0)
        old_risk = getattr(oldest, "risk_score", 0)

        skill_slope = old_risk - new_risk

    # 3. Market Gap
    # Identify which market trends are missing from user's languages
    user_langs = metrics.get("languages", {})
    if not isinstance(user_langs, dict):
        user_langs = {}

    user_skills = set(user_langs.keys())
    market_gap = [skill for skill in MARKET_TRENDS if skill not in user_skills]

    return {
        "commit_velocity": commit_velocity,
        "skill_slope": skill_slope,
        "market_gap": market_gap,
        # Keep legacy key just in case, though we primarily use commit_velocity now
        "commit_trend": commit_velocity
    }
