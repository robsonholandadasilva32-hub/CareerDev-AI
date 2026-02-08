import unittest
from unittest.mock import MagicMock, ANY
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.audit_service import audit_service
from app.services.model_monitor import model_monitor
from app.db.models.governance import GovernanceLog
from app.db.models.ml_risk_log import MLRiskLog

class TestSystemGovernance(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock(spec=Session)

    def test_audit_service_compliance_summary(self):
        # Setup mock for count
        self.mock_db.query.return_value.filter.return_value.count.return_value = 42

        # Setup mock for last activity
        mock_event = MagicMock()
        mock_event.timestamp = datetime.utcnow()
        self.mock_db.query.return_value.order_by.return_value.first.return_value = mock_event

        summary = audit_service.get_compliance_summary(self.mock_db, 1)

        self.assertEqual(summary["total_events_logged"], 42)
        self.assertEqual(summary["status"], "ACTIVE")
        self.assertIsNotNone(summary["last_activity"])

    def test_audit_service_compliance_summary_no_data(self):
        # Setup mock for count = 0
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Setup mock for last activity = None
        self.mock_db.query.return_value.order_by.return_value.first.return_value = None

        summary = audit_service.get_compliance_summary(self.mock_db, 1)

        self.assertEqual(summary["total_events_logged"], 0)
        self.assertEqual(summary["status"], "IDLE")
        self.assertIsNone(summary["last_activity"])

    def test_cleanup_governance_logs(self):
        self.mock_db.query.return_value.filter.return_value.delete.return_value = 100

        deleted = audit_service.cleanup_governance_logs(self.mock_db)

        self.assertEqual(deleted, 100)
        self.mock_db.commit.assert_called_once()

    def test_model_monitor_healthy(self):
        # Create mock logs with varied scores
        logs = [
            MagicMock(final_risk=50),
            MagicMock(final_risk=55),
            MagicMock(final_risk=45),
            MagicMock(final_risk=60),
            MagicMock(final_risk=40),
            MagicMock(final_risk=52)
        ]
        self.mock_db.query.return_value.filter.return_value.all.return_value = logs

        health = model_monitor.check_health(self.mock_db)

        self.assertEqual(health["status"], "HEALTHY")
        self.assertEqual(health["score"], 95)
        self.assertIn("Variance", health["message"])

    def test_model_monitor_frozen(self):
        # Create mock logs with identical scores (low variance)
        logs = [MagicMock(final_risk=50)] * 10
        self.mock_db.query.return_value.filter.return_value.all.return_value = logs

        health = model_monitor.check_health(self.mock_db)

        self.assertEqual(health["status"], "FROZEN")
        self.assertEqual(health["score"], 20)
        self.assertIn("static", health["message"])

    def test_model_monitor_critical_out_of_bounds(self):
        # Create mock logs with one out of bounds
        logs = [
            MagicMock(final_risk=50),
            MagicMock(final_risk=105)
        ]
        self.mock_db.query.return_value.filter.return_value.all.return_value = logs

        health = model_monitor.check_health(self.mock_db)

        self.assertEqual(health["status"], "CRITICAL")
        self.assertEqual(health["score"], 0)
        self.assertIn("invalid", health["message"])

    def test_model_monitor_cold_start(self):
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        health = model_monitor.check_health(self.mock_db)

        self.assertEqual(health["status"], "COLD_START")
        self.assertEqual(health["score"], 100)

if __name__ == '__main__':
    unittest.main()
