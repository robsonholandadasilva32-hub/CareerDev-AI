import unittest
from unittest.mock import MagicMock, patch
from app.services.counterfactual_engine import counterfactual_engine

class TestCounterfactualEngineShap(unittest.TestCase):

    @patch("app.services.counterfactual_engine.shap_explainer.explain")
    def test_generate_uses_shap(self, mock_explain):
        # Mock SHAP output
        # avg_confidence increases risk (positive contribution), commit_velocity decreases risk (negative)
        mock_explain.return_value = {
            "features": {
                "avg_confidence": 2.5,  # High risk driver -> Action: Improve confidence
                "commit_velocity": -1.0 # Reduces risk -> No action needed
            }
        }

        features = {
            "avg_confidence": 50,
            "commit_velocity": 30,
            "market_gap": ["Rust"]
        }
        current_risk = 80

        result = counterfactual_engine.generate(features, current_risk)

        # Verify SHAP explainer was called
        mock_explain.assert_called_with(50, 30)

        # Check actions
        # 1. "avg_confidence" contribution is 2.5 -> impact = 25% risk -> Action generated
        # 2. "commit_velocity" is negative -> No action generated
        # 3. "market_gap" is present -> Hybrid action generated (15% impact)

        actions = result["actions"]
        self.assertEqual(len(actions), 2)

        # Verify Action 1: Confidence
        self.assertIn("Improve verified skill confidence", actions[0])
        self.assertIn("-25% risk", actions[0])

        # Verify Action 2: Market Gap (Hybrid)
        self.assertIn("Practice Rust for 4 weeks", actions[1])
        self.assertIn("-15% risk", actions[1])

        # Verify Projected Risk
        # Total reduction = 25 + 15 = 40
        # Projected = 80 - 40 = 40
        self.assertEqual(result["projected_risk"], 40)

    @patch("app.services.counterfactual_engine.shap_explainer.explain")
    def test_generate_shap_commit_velocity_action(self, mock_explain):
        # Mock SHAP output where commit_velocity is a risk driver
        mock_explain.return_value = {
            "features": {
                "avg_confidence": -0.5, # Good
                "commit_velocity": 1.2  # Bad (risk driver)
            }
        }

        features = {
            "avg_confidence": 90,
            "commit_velocity": 2
        }
        current_risk = 60

        result = counterfactual_engine.generate(features, current_risk)

        actions = result["actions"]
        self.assertEqual(len(actions), 1)
        self.assertIn("Increase commit velocity", actions[0])
        self.assertIn("-12% risk", actions[0]) # 1.2 * 10 = 12

        self.assertEqual(result["projected_risk"], 60 - 12)

if __name__ == "__main__":
    unittest.main()
