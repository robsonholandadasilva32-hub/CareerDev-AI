import sys
import os
from unittest.mock import MagicMock
from statistics import mean, pstdev

# Mock DB models before importing service
from app.db.models.career import CareerProfile
from app.db.models.analytics import RiskSnapshot

# Import the service
from app.services.team_health_engine import team_health_engine

def test_team_burnout_risk():
    db = MagicMock()
    user = MagicMock()
    user.career_profile.team = "Engineering"

    # Mock data: 5 users with risk scores [20, 30, 40, 80, 90]
    # Average: 52
    # Variance (pstdev): ~27.12
    # Burnout Score: (52 * 0.6) + (27.12 * 0.4) = 31.2 + 10.84 = 42.04 -> 42
    # Level: MEDIUM (>= 30)

    scores = [20, 30, 40, 80, 90]

    # Mocking the query chain
    # db.query().join().filter().order_by().limit().all()
    mock_query = db.query.return_value
    mock_join = mock_query.join.return_value
    mock_filter = mock_join.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_limit = mock_order.limit.return_value

    # Return list of tuples (risk_score,)
    mock_limit.all.return_value = [(s,) for s in scores]

    result = team_health_engine.team_burnout_risk(db, user)

    assert result is not None
    assert result['avg_risk'] == 52
    # int(pstdev([20, 30, 40, 80, 90])) -> int(27.129...) -> 27
    assert result['variance'] == int(pstdev(scores))
    assert result['burnout_score'] == 42
    assert result['level'] == "MEDIUM"

def test_simulate_member_exit():
    db = MagicMock()
    user = MagicMock()
    user.career_profile.team = "Engineering"

    # Mock data:
    # User A: 10 (Anchor)
    # User B: 50
    # User C: 60
    # Current Avg: (10+50+60)/3 = 40
    # If Anchor (10) leaves: (50+60)/2 = 55
    # Impact: +15

    raw_data = [
        (1, 10), # User 1, Score 10
        (2, 50),
        (3, 60)
    ]

    # Mock query chain
    mock_query = db.query.return_value
    mock_join = mock_query.join.return_value
    mock_filter = mock_join.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = raw_data

    result = team_health_engine.simulate_member_exit(db, user)

    assert result is not None
    assert result['current_avg'] == 40
    assert result['new_avg_if_exit'] == 55
    assert result['impact'] == 15
    assert result['anchor_score'] == 10

def test_simulate_member_exit_duplicate_anchor():
    db = MagicMock()
    user = MagicMock()
    user.career_profile.team = "Engineering"

    # Mock data:
    # User A: 10 (Anchor 1)
    # User B: 10 (Anchor 2)
    # User C: 70
    # Current Avg: (10+10+70)/3 = 30
    # If ONE Anchor (10) leaves: (10+70)/2 = 40
    # Impact: +10
    # If BOTH left (bug): (70)/1 = 70. Impact +40.

    raw_data = [
        (1, 10),
        (2, 10),
        (3, 70)
    ]

    mock_query = db.query.return_value
    mock_join = mock_query.join.return_value
    mock_filter = mock_join.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = raw_data

    result = team_health_engine.simulate_member_exit(db, user)

    assert result is not None
    assert result['current_avg'] == 30
    assert result['new_avg_if_exit'] == 40
    assert result['impact'] == 10
    assert result['anchor_score'] == 10
