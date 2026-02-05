from app.ml.feature_store import compute_features

class MockSnapshot:
    def __init__(self, risk_score):
        self.risk_score = risk_score

def test_compute_features_with_none_metrics():
    # Should not crash
    result = compute_features(None, [])
    assert result["commit_velocity"] == 0
    assert result["commit_trend"] == 0
    assert isinstance(result["market_gap"], list)

def test_compute_features_with_list_metrics():
    # Should not crash even if metrics is wrong type
    result = compute_features([], [])
    assert result["commit_velocity"] == 0

def test_compute_features_with_valid_metrics():
    metrics = {"commits_last_30_days": 10, "languages": {"Python": 1000}}
    result = compute_features(metrics, [])
    assert result["commit_velocity"] == 10
    # Python is in MARKET_TRENDS, so it should NOT be in market_gap
    assert "Python" not in result["market_gap"]
    # Rust is in MARKET_TRENDS, so it SHOULD be in market_gap (since it's missing)
    assert "Rust" in result["market_gap"]

def test_compute_features_skill_slope_improvement():
    # Improvement: Risk Decreased.
    # Newest (0) = 20. Oldest (-1) = 50.
    # Slope = Old - New = 50 - 20 = 30.
    snapshots = [MockSnapshot(20), MockSnapshot(50)]
    result = compute_features({}, snapshots)
    assert result["skill_slope"] == 30

def test_compute_features_skill_slope_decline():
    # Decline: Risk Increased.
    # Newest (0) = 80. Oldest (-1) = 50.
    # Slope = Old - New = 50 - 80 = -30.
    snapshots = [MockSnapshot(80), MockSnapshot(50)]
    result = compute_features({}, snapshots)
    assert result["skill_slope"] == -30
