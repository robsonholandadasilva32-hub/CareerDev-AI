import sys
import unittest
from unittest.mock import MagicMock
from statistics import mean

# Mock heavy dependencies if needed, but for unit tests with mocks it's usually fine.
# Just ensuring we can import the service.

# We need to mock the models before importing the service if they are not available
# But usually we can import them if the environment is set up.
# Let's assume the environment is set up as per previous tests.

from app.services.team_health_engine import team_health_engine

class TestTeamHealthEngine(unittest.TestCase):

    def setUp(self):
        self.db = MagicMock()
        self.user = MagicMock()
        self.user.id = 1
        self.user.career_profile.team = "Engineering"

    def test_simulate_member_exit_regression(self):
        """
        Verify existing functionality: Simulate Exit (Bus Factor).
        """
        print("\n--- Testing simulate_member_exit (Regression) ---")
        # Mock data:
        # User 1 (Anchor): 10
        # User 2: 50
        # User 3: 60
        # Avg: 40. Without Anchor: 55. Impact: +15.

        raw_data = [
            (1, 10),
            (2, 50),
            (3, 60)
        ]

        # Mock query chain
        mock_query = self.db.query.return_value
        mock_join = mock_query.join.return_value
        mock_filter = mock_join.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = raw_data

        result = team_health_engine.simulate_member_exit(self.db, self.user)

        print(f"Result: {result}")

        self.assertIsNotNone(result)
        self.assertEqual(result['current_avg'], 40)
        self.assertEqual(result['new_avg_if_exit'], 55)
        self.assertEqual(result['impact'], 15)
        self.assertEqual(result['anchor_score'], 10)

    def test_internal_health_ranking(self):
        """
        Verify new functionality: Internal Health Ranking.
        """
        print("\n--- Testing internal_health_ranking ---")
        # Mock data with duplicates to test deduplication
        # User 1 (Me): 20 (Latest), 25 (Old) -> Should use 20
        # User 2: 80
        # User 3: 50

        # Raw data returned by query (ordered by recorded_at desc)
        raw_data = [
            (1, 20), # Latest for User 1
            (2, 80), # Latest for User 2
            (1, 25), # Older for User 1 (Should be ignored)
            (3, 50)  # Latest for User 3
        ]

        # Mock query chain
        mock_query = self.db.query.return_value
        mock_join = mock_query.join.return_value
        mock_filter = mock_join.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = raw_data

        ranking = team_health_engine.internal_health_ranking(self.db, self.user)

        # Calculate expected values
        # Scores: [20, 80, 50] -> Avg: 50
        # User 1: 20 - 50 = -30.0
        # User 2: 80 - 50 = +30.0
        # User 3: 50 - 50 = 0.0

        print("Ranking Output:")
        for r in ranking:
            print(r)

        self.assertEqual(len(ranking), 3)

        # Verify Sorting (Risk Ascending)
        self.assertEqual(ranking[0]['user_id'], 1) # Score 20
        self.assertEqual(ranking[1]['user_id'], 3) # Score 50
        self.assertEqual(ranking[2]['user_id'], 2) # Score 80

        # Verify Values for User 1 (Me)
        user1 = ranking[0]
        self.assertEqual(user1['risk'], 20)
        self.assertTrue(user1['is_current_user'])
        self.assertEqual(user1['contribution'], -30.0)

        # Verify Values for User 2
        user2 = ranking[2]
        self.assertEqual(user2['risk'], 80)
        self.assertFalse(user2['is_current_user'])
        self.assertEqual(user2['contribution'], 30.0)

    def test_internal_health_ranking_empty(self):
        """
        Verify handling of empty data.
        """
        print("\n--- Testing internal_health_ranking (Empty) ---")
        mock_query = self.db.query.return_value
        mock_join = mock_query.join.return_value
        mock_filter = mock_join.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = []

        ranking = team_health_engine.internal_health_ranking(self.db, self.user)
        self.assertEqual(ranking, [])

if __name__ == '__main__':
    unittest.main()
