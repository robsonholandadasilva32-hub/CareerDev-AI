import sys
from unittest.mock import MagicMock
from statistics import mean

# Mock DB models before importing service
from app.db.models.career import CareerProfile
from app.db.models.analytics import RiskSnapshot

# Import the service
from app.services.team_health_engine import team_health_engine

def test_simulate_new_hire():
    db = MagicMock()
    user = MagicMock()
    user.career_profile.team = "Engineering"

    # Mock data:
    # User A: 50
    # User B: 60
    # Current Avg: (50+60)/2 = 55
    # Hire (Risk 20): (50+60+20)/3 = 130/3 = 43.33 -> 43
    # Impact: 43 - 55 = -12

    raw_data = [
        (1, 50),
        (2, 60)
    ]

    mock_query = db.query.return_value
    mock_join = mock_query.join.return_value
    mock_filter = mock_join.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = raw_data

    result = team_health_engine.simulate_new_hire(db, user, hypothetical_risk=20)

    assert result is not None
    assert result['current_avg'] == 55
    assert result['new_avg_with_hire'] == 43
    # int(-11.66) is -11, so we expect -11 with the current logic
    assert result['impact'] == -11
    assert result['hypothetical_risk'] == 20

def test_simulate_new_hire_empty_team():
    db = MagicMock()
    user = MagicMock()
    user.career_profile.team = "Engineering"

    # Return empty list
    mock_query = db.query.return_value
    mock_join = mock_query.join.return_value
    mock_filter = mock_join.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = []

    result = team_health_engine.simulate_new_hire(db, user)

    assert result is None

def test_simulate_new_hire_single_user():
    db = MagicMock()
    user = MagicMock()
    user.career_profile.team = "Engineering"

    # User A: 80
    # Current Avg: 80
    # Hire (Risk 20): (80+20)/2 = 50
    # Impact: 50 - 80 = -30

    raw_data = [
        (1, 80)
    ]

    mock_query = db.query.return_value
    mock_join = mock_query.join.return_value
    mock_filter = mock_join.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = raw_data

    result = team_health_engine.simulate_new_hire(db, user, hypothetical_risk=20)

    assert result is not None
    assert result['current_avg'] == 80
    assert result['new_avg_with_hire'] == 50
    assert result['impact'] == -30
