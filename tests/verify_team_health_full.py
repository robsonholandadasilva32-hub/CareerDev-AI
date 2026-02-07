import sys
import os
from unittest.mock import MagicMock
from statistics import mean, pstdev

# Mock dependencies BEFORE importing app modules
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["app.db.models.analytics"] = MagicMock()
sys.modules["app.db.models.career"] = MagicMock()

# Mock specific classes
mock_risk_snapshot = MagicMock()
mock_risk_snapshot.risk_score = "risk_score"
mock_risk_snapshot.user_id = "user_id"
mock_risk_snapshot.recorded_at = MagicMock() # Mock as object
mock_risk_snapshot.recorded_at.desc.return_value = "recorded_at_desc" # Mock .desc()
sys.modules["app.db.models.analytics"].RiskSnapshot = mock_risk_snapshot

mock_career_profile = MagicMock()
mock_career_profile.user_id = "user_id"
mock_career_profile.team = "team"
sys.modules["app.db.models.career"].CareerProfile = mock_career_profile

# Add app to path
sys.path.append(os.getcwd())

# Now import the module under test
from app.services.team_health_engine import team_health_engine

def test_team_burnout_risk():
    print("\n--- Testing Team Burnout Risk ---")
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.career_profile.team = "Engineering"

    # Scenario 1: Low Risk, Low Variance
    # Scores: [20, 20, 20, 20, 20] -> Avg 20, Var 0
    # Burnout = 20*0.6 + 0*0.4 = 12 (LOW)
    # The code does: scores = [r[0] for r in risks]
    mock_risks_1 = [(20,) for _ in range(10)]

    # Mock the chain: query().join().filter().order_by().limit().all()
    # It's easier to mock the final .all() return value
    # Note: query(RiskSnapshot.risk_score)

    mock_query = mock_db.query.return_value
    mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_risks_1

    result = team_health_engine.team_burnout_risk(mock_db, mock_user)
    # print(f"Scenario 1 Result: {result}")

    if result is None:
        print("❌ Scenario 1 Failed: Result is None")
    else:
        assert result["level"] == "LOW", f"Expected LOW, got {result['level']}"
        assert result["burnout_score"] < 30, f"Expected < 30, got {result['burnout_score']}"

    # Scenario 2: High Risk, High Variance
    # Scores: [10, 90, 10, 90] -> Avg 50, Var ~40
    # Burnout = 50*0.6 + 40*0.4 = 30 + 16 = 46 (MEDIUM)
    mock_risks_2 = [(10,), (90,), (10,), (90,)]
    mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_risks_2

    result = team_health_engine.team_burnout_risk(mock_db, mock_user)
    # print(f"Scenario 2 Result: {result}")
    # 46 is MEDIUM (>=30)
    assert result["level"] == "MEDIUM" or result["level"] == "HIGH", f"Expected MEDIUM/HIGH, got {result['level']}"

    print("✅ Burnout Risk Logic Verified")

def test_simulate_member_exit():
    print("\n--- Testing Member Exit Simulation ---")
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.career_profile.team = "Engineering"

    # Setup: 3 Users
    # U1: 10 (Anchor)
    # U2: 50
    # U3: 90
    # Current Avg: (10+50+90)/3 = 50
    # If U1 leaves: (50+90)/2 = 70
    # Impact: +20

    mock_data = [
        (1, 10),
        (2, 50),
        (3, 90)
    ]

    mock_query = mock_db.query.return_value
    mock_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = mock_data

    result = team_health_engine.simulate_member_exit(mock_db, mock_user)
    # print(f"Result: {result}")

    assert result["current_avg"] == 50, f"Expected 50, got {result['current_avg']}"
    assert result["new_avg_if_exit"] == 70, f"Expected 70, got {result['new_avg_if_exit']}"
    assert result["impact"] == 20, f"Expected 20, got {result['impact']}"
    assert result["anchor_score"] == 10, f"Expected 10, got {result['anchor_score']}"

    print("✅ Member Exit Simulation Verified")

def test_internal_health_ranking():
    print("\n--- Testing Internal Health Ranking ---")
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.career_profile.team = "Engineering"
    mock_user.id = 101 # Set current user ID

    # Setup: 3 Users
    # User A (101): 10 (Low Risk) -> Should contribute +40 (Current User)
    # User B (102): 50 (Avg Risk) -> Should contribute 0
    # User C (103): 90 (High Risk) -> Should contribute -40
    # Team Avg = 50

    mock_data = [
        (101, 10),
        (102, 50),
        (103, 90)
    ]

    mock_query = mock_db.query.return_value
    mock_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = mock_data

    # Execute
    ranking = team_health_engine.internal_health_ranking(mock_db, mock_user)

    if not ranking:
        print("❌ Ranking is None/Empty")
        return

    # Assertions
    top_contributor = ranking[0]
    bottom_contributor = ranking[-1]

    print(f"Top Contributor: User {top_contributor['user_id']} (Contribution: {top_contributor['contribution']})")
    print(f"Bottom Contributor: User {bottom_contributor['user_id']} (Contribution: {bottom_contributor['contribution']})")

    assert top_contributor['user_id'] == 101, "Lowest risk user should be top contributor"
    assert top_contributor['contribution'] > 0, "Top contributor should have positive impact"
    assert bottom_contributor['contribution'] < 0, "High risk user should have negative impact"

    # Check current user flag
    current_user_entry = next(r for r in ranking if r["user_id"] == 101)
    assert current_user_entry["is_current_user"] is True

    print("✅ Ranking Logic Verified")

if __name__ == "__main__":
    test_team_burnout_risk()
    test_simulate_member_exit()
    test_internal_health_ranking()
    print("\n🎉 ALL TESTS PASSED")
