from app.ml.feature_store import compute_features

def test_compute_features_with_none_metrics():
    # Should not crash
    result = compute_features(None, [])
    assert result["commit_trend"] == 0

def test_compute_features_with_list_metrics():
    # Should not crash
    result = compute_features([], [])
    assert result["commit_trend"] == 0

def test_compute_features_with_valid_metrics():
    metrics = {"commits_last_30_days": 10}
    result = compute_features(metrics, [])
    assert result["commit_trend"] == 10
