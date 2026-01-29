import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

MODEL_PATH = "app/ml/risk_model.joblib"

class RiskForecastModel:
    def __init__(self):
        self.model = LinearRegression()

    def train(self, csv_path: str):
        df = pd.read_csv(csv_path)

        X = df[["confidence"]].fillna(0)
        y = df["risk"].fillna(0)

        self.model.fit(X, y)
        joblib.dump(self.model, MODEL_PATH)

    def predict(self, avg_confidence: float) -> int:
        model = joblib.load(MODEL_PATH)
        prediction = model.predict([[avg_confidence]])[0]
        return max(0, min(int(prediction), 100))
