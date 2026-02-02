def compute_features(metrics, snapshots):
    # Defensive programming: Ensure metrics is a dict to prevent crashes
    if not isinstance(metrics, dict):
        metrics = {}

    skill_slope = 0
    if snapshots:
        skill_slope = snapshots[-1].confidence_score - snapshots[0].confidence_score

    return {
        # Defensive access to prevent KeyError if metrics are missing
        "commit_trend": metrics.get("commits_last_30_days", 0),
        "skill_slope": skill_slope
    }
