
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from app.services.trust_engine import trust_engine
from app.services.audit_service import audit_service
from app.db.models.governance import GovernanceLog

def test_trust_engine_logic():
    # Scenario 1: Perfect System
    status = {"status": "HEALTHY"}
    last_snap = datetime.utcnow()
    res = trust_engine.calculate_trust(last_snap, status)
    assert res["trust_score"] == 100
    assert res["level"] == "HIGH"
    assert len(res["penalties"]) == 0

    # Scenario 2: Stale Data
    last_snap_stale = datetime.utcnow() - timedelta(days=8)
    res = trust_engine.calculate_trust(last_snap_stale, status)
    assert res["trust_score"] == 70  # 100 - 30
    assert "stale" in res["penalties"][0]

    # Scenario 3: Broken Audit
    bad_status = {"status": "WARNING", "message": "Down"}
    res = trust_engine.calculate_trust(last_snap, bad_status)
    assert res["trust_score"] == 80 # 100 - 20
    assert "Audit System Issue" in res["penalties"][0]

    # Scenario 4: Cold Start (No Snapshot)
    res = trust_engine.calculate_trust(None, status)
    assert res["trust_score"] == 50 # 100 - 50
    assert "No historical data" in res["penalties"][0]

def test_audit_service_mock():
    # Mock DB Session
    mock_db = MagicMock()

    # Case 1: Logs exist
    mock_db.query.return_value.filter.return_value.count.return_value = 5
    res = audit_service.check_system_integrity(mock_db)
    assert res["status"] == "HEALTHY"

    # Case 2: No logs
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    res = audit_service.check_system_integrity(mock_db)
    assert res["status"] == "WARNING"
