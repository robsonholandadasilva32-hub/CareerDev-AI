def compute_features(metrics, snapshots):
    return {
        "commit_trend": metrics["commits_last_30_days"],
        "skill_slope": snapshots[-1].confidence_score - snapshots[0].confidence_score
    }
