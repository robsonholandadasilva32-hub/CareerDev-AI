import unittest
from unittest.mock import MagicMock, patch, Mock
import numpy as np
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.ml.shap_explainer import ShapRiskExplainer, shap_explainer

class TestShapExplainer(unittest.TestCase):

    def setUp(self):
        self.explainer = ShapRiskExplainer()

    @patch("app.ml.shap_explainer.os.path.exists")
    @patch("app.ml.shap_explainer.joblib.load")
    @patch("app.ml.shap_explainer.shap.Explainer")
    def test_explain_success(self, mock_shap_explainer_cls, mock_joblib_load, mock_exists):
        """Test that explain returns correct structure when model exists."""
        # Setup mocks
        mock_exists.return_value = True
        mock_model = Mock()
        mock_joblib_load.return_value = mock_model

        # Mock SHAP explainer instance
        mock_shap_instance = Mock()
        mock_shap_explainer_cls.return_value = mock_shap_instance

        # Mock return value of explainer(X)
        # It returns a generic object with a .values attribute
        mock_shap_values = Mock()
        # Simulate shap values for 2 features: avg_confidence (0.5), commit_velocity (-0.2)
        mock_shap_values.values = np.array([[0.5, -0.2]])
        mock_shap_instance.return_value = mock_shap_values

        # Execute
        result = self.explainer.explain(avg_confidence=80, commit_velocity=10)

        # Verify
        mock_exists.assert_called_with("app/ml/models/risk_model_v1.1.0.joblib")
        mock_joblib_load.assert_called()
        mock_shap_explainer_cls.assert_called_with(mock_model)

        # Check X structure passed to explainer
        # args[0] is X
        call_args = mock_shap_instance.call_args
        self.assertIsNotNone(call_args)
        X_arg = call_args[0][0]
        self.assertTrue(np.array_equal(X_arg, np.array([[80, 10]])))

        # Check Result
        self.assertEqual(result["features"]["avg_confidence"], 0.5)
        self.assertEqual(result["features"]["commit_velocity"], -0.2)

    @patch("app.ml.shap_explainer.os.path.exists")
    def test_explain_fallback_missing_file(self, mock_exists):
        """Test fallback when model file is missing."""
        mock_exists.return_value = False

        result = self.explainer.explain(avg_confidence=80, commit_velocity=10)

        # Should return heuristic fallback
        self.assertEqual(result["features"]["avg_confidence"], 0.5)
        self.assertEqual(result["features"]["commit_velocity"], 0.0)

    @patch("app.ml.shap_explainer.os.path.exists")
    @patch("app.ml.shap_explainer.joblib.load")
    def test_explain_fallback_exception(self, mock_joblib_load, mock_exists):
        """Test fallback when an exception occurs during loading/prediction."""
        mock_exists.return_value = True
        mock_joblib_load.side_effect = Exception("Corrupted file")

        result = self.explainer.explain(avg_confidence=80, commit_velocity=10)

        # Should return heuristic fallback
        self.assertEqual(result["features"]["avg_confidence"], 0.5)
        self.assertEqual(result["features"]["commit_velocity"], 0.0)

if __name__ == "__main__":
    unittest.main()
