import os
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from typing import Optional, Dict

# =========================================================
# MODEL CONFIGURATION
# =========================================================

MODEL_VERSION = "1.1.0"

MODEL_DIR = "app/ml/models"
LEGACY_MODEL_PATH = "app/ml/risk_model.joblib"
VERSIONED_MODEL_PATH = f"{MODEL_DIR}/risk_model_v{MODEL_VERSION}.joblib"


# =========================================================
# RISK FORECAST MODEL
# =========================================================

class RiskForecastModel:
    """
    Unified Risk Forecast Model

    Supports:
    - Legacy mode (confidence only)
    - Advanced mode (confidence + commit velocity)
    - Explicit versioning
    - Safe fallback when model is missing
    """

    def __init__(self):
        self.model = LinearRegression()
        self.version = MODEL_VERSION

    # -----------------------------------------------------
    # TRAINING
    # -----------------------------------------------------

    def train(self, csv_path: str, advanced: bool = True):
        """
        Train and persist the model.

        advanced=True  -> uses avg_confidence + commit_velocity
        advanced=False -> legacy confidence-only model
        """
        df = pd.read_csv(csv_path)

        if advanced:
            X = df[["avg_confidence", "commit_velocity"]].fillna(0)
            y = df["risk_score"].fillna(0)
            path = VERSIONED_MODEL_PATH
        else:
            X = df[["confidence"]].fillna(0)
            y = df["risk"].fillna(0)
            path = LEGACY_MODEL_PATH

        self.model.fit(X, y)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self.model, path)

    # -----------------------------------------------------
    # PREDICTION (SAFE + COMPATIBLE)
    # -----------------------------------------------------

    def predict(
        self,
        avg_confidence: float,
        commit_velocity: Optional[float] = None
    ) -> Dict:
        """
        Predict risk score.

        If commit_velocity is provided:
            -> uses versioned model (v1.1+)
        Else:
            -> falls back to legacy model
        """
        # ---------- Advanced path ----------
        if commit_velocity is not None and os.path.exists(VERSIONED_MODEL_PATH):
            model = joblib.load(VERSIONED_MODEL_PATH)
            raw_pred = model.predict([[avg_confidence, commit_velocity]])[0]

            return {
                "ml_risk": self._normalize(raw_pred),
                "model_version": self.version,
                "mode": "advanced"
            }

        # ---------- Legacy fallback ----------
        if os.path.exists(LEGACY_MODEL_PATH):
            model = joblib.load(LEGACY_MODEL_PATH)
            raw_pred = model.predict([[avg_confidence]])[0]

            return {
                "ml_risk": self._normalize(raw_pred),
                "model_version": "legacy",
                "mode": "legacy"
            }

        # ---------- Hard fallback (no model) ----------
        return {
            "ml_risk": self._heuristic_fallback(avg_confidence),
            "model_version": "heuristic",
            "mode": "fallback"
        }

    # -----------------------------------------------------
    # INTERNAL HELPERS
    # -----------------------------------------------------

    @staticmethod
    def _normalize(value: float) -> int:
        """Clamp prediction to [0, 100]."""
        return max(0, min(int(value), 100))

    @staticmethod
    def _heuristic_fallback(avg_confidence: float) -> int:
        """
        Safety net if no trained model exists.
        Inverse confidence heuristic.
        """
        return max(0, min(int(100 - avg_confidence), 100))
