import sys
from unittest.mock import MagicMock

# MOCK HEAVY LIBS BEFORE IMPORTS
sys.modules["tensorflow"] = MagicMock()
sys.modules["tensorflow.keras"] = MagicMock()
sys.modules["tensorflow.keras.models"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["mlflow"] = MagicMock()
sys.modules["joblib"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["shap"] = MagicMock()
sys.modules["github"] = MagicMock()

import pytest
from datetime import datetime, timedelta
# We need to ensure models are loaded or mocked properly if imports happen
# But benchmark_engine only imports RiskSnapshot and CareerProfile
from app.services.benchmark_engine import benchmark_engine
from app.db.models.analytics import RiskSnapshot
from app.db.models.user import User
# Resolving dependencies for User to prevent SQLAlchemy errors
from app.db.models.weekly_routine import WeeklyRoutine
from app.db.models.gamification import UserBadge
from app.db.models.security import UserSession
from app.db.models.career import LearningPlan, CareerProfile
from app.db.models.skill_snapshot import SkillSnapshot
from app.db.models.mentor import MentorMemory
from app.db.models.audit import AuditLog

def test_get_user_history_logic():
    # Mock DB Session
    db = MagicMock()
    user = MagicMock(spec=User)
    user.id = 1

    # Create 15 snapshots
    snapshots = []
    base_time = datetime(2023, 1, 1, 12, 0, 0)
    for i in range(15):
        s = RiskSnapshot(
            user_id=1,
            risk_score=10 + i,
            created_at=base_time + timedelta(days=i)
        )
        snapshots.append(s)

    # Mock DB Query chain
    # filter().order_by().limit().all()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    order_by_mock = MagicMock()
    limit_mock = MagicMock()

    db.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = order_by_mock
    order_by_mock.limit.return_value = limit_mock

    # Simulate descending order limit 12 (newest 12)
    # snapshots[14] is newest
    limit_mock.all.return_value = list(reversed(snapshots[-12:]))

    # Execute
    result = benchmark_engine.get_user_history(db, user)

    # Verify
    assert len(result.values) == 12
    # Check chronological order (Oldest -> Newest)
    # Expected: [13, 14, ..., 24]
    assert result.values[0] == 13
    assert result.values[-1] == 24
    assert result.labels[0] == "04/01"

def test_get_user_history_empty():
    db = MagicMock()
    user = MagicMock(spec=User)

    query_mock = MagicMock()
    db.query.return_value = query_mock
    query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    result = benchmark_engine.get_user_history(db, user)
    assert result is None
