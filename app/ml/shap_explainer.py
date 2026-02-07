import shap
import joblib
import numpy as np
import os
from typing import Dict
from app.ml.risk_forecast_model import VERSIONED_MODEL_PATH

class ShapRiskExplainer:
    """
    Uses SHAP to compute feature contribution and generate quantitative counterfactual deltas.
    """
    def __init__(self):
        self.model = None
        self.explainer = None

    def _load_resources(self):
        if self.model is None:
            if not os.path.exists(VERSIONED_MODEL_PATH):
                raise FileNotFoundError(f"Model not found at {VERSIONED_MODEL_PATH}")
            self.model = joblib.load(VERSIONED_MODEL_PATH)
            # Use specific explainer based on model type (TreeExplainer is faster for forests)
            # For LinearRegression (which is used in risk_forecast_model.py), LinearExplainer is appropriate,
            # but generic Explainer handles most cases automatically.
            self.explainer = shap.Explainer(self.model)

    def explain(self, avg_confidence: float, commit_velocity: float) -> Dict:
        """
        Explain the risk score using SHAP values.

        Args:
            avg_confidence (float): The average skill confidence score.
            commit_velocity (float): The commit velocity metric.

        Returns:
            Dict: A dictionary containing feature contributions.
        """
        try:
            self._load_resources()

            # NOTE: Ensure this array structure matches EXACTLY the training data columns
            # Based on RiskForecastModel.train: X = df[["avg_confidence", "commit_velocity"]]
            X = np.array([[avg_confidence, commit_velocity]])

            shap_values = self.explainer(X)

            # shap_values.values is a matrix (1, n_features)
            contributions = shap_values.values[0]

            return {
                "features": {
                    "avg_confidence": float(contributions[0]),
                    "commit_velocity": float(contributions[1])
                }
            }
        except (FileNotFoundError, OSError, Exception) as e:
            # FALLBACK: Return heuristic values if model is missing or loading fails
            # This ensures the app works immediately after deploy without the artifact
            # Returning dummy positive contributions that mimic a high risk scenario or neutral
            # depending on what the CounterfactualEngine expects.
            # User instruction: "Return heuristic values if model is missing... avg_confidence: 0.5"
            return {
                "features": {
                    "avg_confidence": 0.5, # Dummy positive contribution
                    "commit_velocity": 0.0
                }
            }

    def explain_visual(self, avg_confidence: float, commit_velocity: float):
        """
        Returns data formatted specifically for Chart.js visualization.
        """
        # Ensure resources are loaded (Lazy Loading)
        try:
            self._load_resources()
            X = np.array([[avg_confidence, commit_velocity]])
            shap_values = self.explainer(X)
            contributions = shap_values.values[0]

            return {
                "labels": ["Verified Skill Confidence", "Commit Velocity"],
                "values": [float(contributions[0]), float(contributions[1])]
            }
        except (FileNotFoundError, AttributeError, OSError, Exception):
            # Fallback if model is missing
            return {
                "labels": ["Skill Confidence", "Commit Velocity"],
                "values": [0, 0]
            }

shap_explainer = ShapRiskExplainer()
