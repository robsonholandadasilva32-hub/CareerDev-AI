import pytest
from unittest.mock import MagicMock
from app.services.team_health_engine import team_health_engine
from app.db.models.analytics import RiskSnapshot
from app.db.models.career import CareerProfile

def test_team_burnout_risk_no_profile():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = None

    result = team_health_engine.team_burnout_risk(db, user)
    assert result is None

def test_team_burnout_risk_no_team():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = MagicMock()
    user.career_profile.team = None

    result = team_health_engine.team_burnout_risk(db, user)
    assert result is None

def test_team_burnout_risk_no_data():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = MagicMock()
    user.career_profile.team = "A-Team"

    # Mock empty result
    # The chain is db.query(...).join(...).filter(...).order_by(...).limit(...).all()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    result = team_health_engine.team_burnout_risk(db, user)
    assert result is None

def test_team_burnout_risk_medium():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = MagicMock()
    user.career_profile.team = "A-Team"

    # Mock data: [50, 60, 40]
    # Mean = 50
    # Variance (pstdev) = ~8.16
    # Burnout = int(50*0.6 + 8.16*0.4) = int(30 + 3.26) = 33
    # Level >= 30 is MEDIUM

    mock_risks = [(50,), (60,), (40,)]

    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_risks

    result = team_health_engine.team_burnout_risk(db, user)

    assert result is not None
    assert result["avg_risk"] == 50
    assert result["variance"] == 8
    assert result["burnout_score"] == 33
    assert result["level"] == "MEDIUM"

def test_team_burnout_risk_high():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = MagicMock()
    user.career_profile.team = "A-Team"

    # Mock data: [100, 100]
    # Mean = 100
    # Variance = 0
    # Burnout = 100*0.6 + 0 = 60
    # Level >= 60 is HIGH

    mock_risks = [(100,), (100,)]
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_risks

    result = team_health_engine.team_burnout_risk(db, user)
    assert result["level"] == "HIGH"
    assert result["burnout_score"] == 60

def test_team_burnout_risk_low():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = MagicMock()
    user.career_profile.team = "A-Team"

    # Mock data: [10, 10]
    # Mean = 10
    # Variance = 0
    # Burnout = 6
    # Level < 30 is LOW

    mock_risks = [(10,), (10,)]
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_risks

    result = team_health_engine.team_burnout_risk(db, user)
    assert result["level"] == "LOW"
    assert result["burnout_score"] == 6

def test_team_burnout_risk_single_point():
    db = MagicMock()
    user = MagicMock()
    user.career_profile = MagicMock()
    user.career_profile.team = "A-Team"

    # Mock data: [50]
    # Mean = 50
    # Variance logic: pstdev(scores) if len(scores) > 1 else 0 -> should be 0
    # Burnout = 30 + 0 = 30

    mock_risks = [(50,)]
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_risks

    result = team_health_engine.team_burnout_risk(db, user)
    assert result["variance"] == 0
    assert result["burnout_score"] == 30
