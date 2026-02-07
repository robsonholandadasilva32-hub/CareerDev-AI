import unittest
from unittest.mock import MagicMock
from app.services.benchmark_engine import BenchmarkEngine
from app.db.models.career import CareerProfile
from app.db.models.analytics import RiskSnapshot

class TestTeamBenchmark(unittest.TestCase):
    def setUp(self):
        self.engine = BenchmarkEngine()
        self.mock_db = MagicMock()
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_profile = MagicMock()
        self.mock_user.career_profile = self.mock_profile

    def test_compute_team_org_no_profile(self):
        self.mock_user.career_profile = None
        result = self.engine.compute_team_org(self.mock_db, self.mock_user)
        self.assertIsNone(result)

    def test_compute_team_org_no_snapshot(self):
        # Setup: Profile exists, but no snapshot
        self.mock_profile.organization = "OrgA"
        self.mock_profile.team = "TeamA"

        def query_side_effect(*args):
            if args[0] is RiskSnapshot:
                mock_q = MagicMock()
                mock_q.filter.return_value.order_by.return_value.first.return_value = None
                return mock_q
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect

        result = self.engine.compute_team_org(self.mock_db, self.mock_user)
        self.assertIsNone(result)

    def test_compute_team_org_no_team_no_org(self):
        # Setup: User has no team/org
        self.mock_profile.organization = None
        self.mock_profile.team = None

        # Mock snapshot
        latest_snapshot = MagicMock()
        latest_snapshot.risk_score = 50

        def query_side_effect(*args):
            if args[0] is RiskSnapshot:
                mock_q = MagicMock()
                mock_q.filter.return_value.order_by.return_value.first.return_value = latest_snapshot
                return mock_q
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect

        result = self.engine.compute_team_org(self.mock_db, self.mock_user)
        self.assertIsNone(result)

    def test_compute_team_org_success(self):
        # Setup: User in OrgA, TeamA
        self.mock_profile.organization = "OrgA"
        self.mock_profile.team = "TeamA"

        # Mock snapshot (My risk = 30)
        latest_snapshot = MagicMock()
        latest_snapshot.risk_score = 30

        def query_side_effect(*args):
            if args[0] is RiskSnapshot:
                mock_q = MagicMock()
                mock_q.filter.return_value.order_by.return_value.first.return_value = latest_snapshot
                return mock_q
            else:
                 mock_q = MagicMock()
                 mock_q.join.return_value.filter.return_value.filter.return_value.all.return_value = [
                     (10,), (30,), (80,)
                 ]
                 return mock_q

        self.mock_db.query.side_effect = query_side_effect

        result = self.engine.compute_team_org(self.mock_db, self.mock_user)

        self.assertIsNotNone(result)
        self.assertEqual(result['percentile'], 66)
        self.assertIn("OrgA", result['context'])
        self.assertIn("TeamA", result['context'])
        self.assertIn("safer than 66%", result['message'])

    def test_compute_team_org_single_user(self):
        self.mock_profile.organization = "OrgB"
        self.mock_profile.team = "TeamB"

        latest_snapshot = MagicMock()
        latest_snapshot.risk_score = 50

        def query_side_effect(*args):
            if args[0] is RiskSnapshot:
                mock_q = MagicMock()
                mock_q.filter.return_value.order_by.return_value.first.return_value = latest_snapshot
                return mock_q
            else:
                 mock_q = MagicMock()
                 # Only me
                 mock_q.join.return_value.filter.return_value.filter.return_value.all.return_value = [
                     (50,)
                 ]
                 return mock_q

        self.mock_db.query.side_effect = query_side_effect

        result = self.engine.compute_team_org(self.mock_db, self.mock_user)
        self.assertEqual(result['percentile'], 100)

if __name__ == '__main__':
    unittest.main()
