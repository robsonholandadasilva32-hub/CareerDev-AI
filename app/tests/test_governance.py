import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from datetime import datetime

import app.db.base # Import all models to register mappers
from app.db.models.governance import GovernanceLog
from app.services.audit_service import audit_service
from app.jobs.retention import cleanup_governance_logs

def test_log_event():
    mock_db = MagicMock(spec=Session)

    # Mock add and commit
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()

    log = audit_service.log_event(
        db=mock_db,
        user_id=1,
        event_type="TEST_EVENT",
        severity="INFO",
        details="Test details"
    )

    assert log is not None
    assert log.user_id == 1
    assert log.event_type == "TEST_EVENT"
    assert log.severity == "INFO"

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

def test_get_compliance_summary():
    mock_db = MagicMock(spec=Session)

    # Mock query chain
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value

    # Mock count
    mock_filter.count.return_value = 42

    # Mock last event
    mock_last_event = GovernanceLog(timestamp=datetime(2023, 1, 1))
    mock_filter.order_by.return_value.first.return_value = mock_last_event

    summary = audit_service.get_compliance_summary(mock_db, user_id=1)

    assert summary["total_events_logged"] == 42
    assert summary["last_activity"] == datetime(2023, 1, 1)
    assert summary["data_status"] == "SECURE"
    assert summary["retention_policy"] == "90 Days"

def test_cleanup_governance_logs():
    mock_db = MagicMock(spec=Session)

    # Mock delete
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.delete.return_value = 10

    deleted = cleanup_governance_logs(mock_db, retention_days=90)

    assert deleted == 10
    mock_db.commit.assert_called_once()
    mock_filter.delete.assert_called_once()
