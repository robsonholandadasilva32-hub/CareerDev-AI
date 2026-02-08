import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.career_engine import career_engine
from app.db.models.user import User
from app.db.models.analytics import RiskSnapshot
from app.db.models.governance import GovernanceLog
from app.jobs.retention import cleanup_governance_logs

class TestEarlyWarningSystem(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = 1

    @patch("app.services.career_engine.audit_service")
    def test_risk_spike_critical_detection(self, mock_audit):
        """
        Test that a risk increase of >= 15 triggers a CRITICAL alert and audit log.
        """
        # Setup: Previous risk was 50
        last_snapshot = RiskSnapshot(risk_score=50, recorded_at=datetime.utcnow())

        # Configure DB query mock
        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        order_mock.first.return_value = last_snapshot

        # Act: Current risk is 65 (Delta = 15)
        current_risk = 65
        result = career_engine._check_risk_spike(self.mock_db, self.mock_user, current_risk)

        # Assert: Alert Generated
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "SPIKE")
        self.assertEqual(result["level"], "CRITICAL")
        self.assertEqual(result["delta"], 15)

        # Assert: Audit Log Created
        mock_audit.log_event.assert_called_once_with(
            db=self.mock_db,
            event_type="RISK_SPIKE",
            severity="CRITICAL",
            details="Risk spiked by +15% (Old: 50, New: 65)",
            user_id=1
        )

    @patch("app.services.career_engine.audit_service")
    def test_risk_spike_below_threshold(self, mock_audit):
        """
        Test that a risk increase of < 15 does NOT trigger an alert.
        """
        last_snapshot = RiskSnapshot(risk_score=50, recorded_at=datetime.utcnow())

        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        order_mock.first.return_value = last_snapshot

        # Act: Current risk 60 (Delta = 10)
        current_risk = 60
        result = career_engine._check_risk_spike(self.mock_db, self.mock_user, current_risk)

        # Assert
        self.assertIsNone(result)
        mock_audit.log_event.assert_not_called()

    @patch("app.services.career_engine.audit_service")
    def test_risk_decrease(self, mock_audit):
        """
        Test that a risk decrease does NOT trigger an alert.
        """
        last_snapshot = RiskSnapshot(risk_score=50, recorded_at=datetime.utcnow())

        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        order_mock.first.return_value = last_snapshot

        # Act: Current risk 40 (Delta = -10)
        current_risk = 40
        result = career_engine._check_risk_spike(self.mock_db, self.mock_user, current_risk)

        # Assert
        self.assertIsNone(result)
        mock_audit.log_event.assert_not_called()

    @patch("app.services.career_engine.audit_service")
    def test_no_previous_snapshot(self, mock_audit):
        """
        Test behavior when no previous snapshot exists (first run).
        """
        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        order_mock.first.return_value = None

        current_risk = 50
        result = career_engine._check_risk_spike(self.mock_db, self.mock_user, current_risk)

        self.assertIsNone(result)
        mock_audit.log_event.assert_not_called()

    def test_retention_policy_cleanup(self):
        """
        Test that cleanup_governance_logs issues a delete query for old records.
        """
        # Mock Query Chain
        query_mock = self.mock_db.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.delete.return_value = 10 # Simulate 10 deleted rows

        # Act
        cleanup_governance_logs(self.mock_db, retention_days=90)

        # Assert
        # Check that query was called on GovernanceLog model
        self.mock_db.query.assert_called_with(GovernanceLog)

        # Verify filter was applied (can't easily verify exact datetime in mock, but can verify call structure)
        query_mock.filter.assert_called()
        filter_mock.delete.assert_called()
        self.mock_db.commit.assert_called()

if __name__ == "__main__":
    unittest.main()
