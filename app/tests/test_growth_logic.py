import pytest
from unittest.mock import MagicMock
import app.db.base  # Ensure all models are loaded
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.db.models.gamification import UserBadge
from app.db.models.security import AuditLog, UserSession
from app.services.growth_engine import growth_engine

def test_hardcore_mode_activation():
    # Setup
    user = User(id=1, streak_count=5)
    user.career_profile = CareerProfile(user_id=1, github_activity_metrics={"raw_languages": {"Python": 1000}})
    mock_db = MagicMock()

    # Action
    plan = growth_engine.generate_weekly_plan(mock_db, user)

    # Assert
    assert plan["focus_language"] == "System Design"
    assert "HARDCORE MODE ACTIVE" in plan["reasoning"]
    assert any("Design" in t["type"] for t in plan["routine"])

def test_normal_mode():
    # Setup
    user = User(id=1, streak_count=1)
    user.career_profile = CareerProfile(user_id=1, github_activity_metrics={"raw_languages": {"Python": 1000}})
    mock_db = MagicMock()

    # Action
    plan = growth_engine.generate_weekly_plan(mock_db, user)

    # Assert
    assert plan["focus_language"] != "System Design" # Assuming normal logic picks Python or Rust
    assert "HARDCORE MODE" not in plan["reasoning"]
