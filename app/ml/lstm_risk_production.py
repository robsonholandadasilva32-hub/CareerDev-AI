import numpy as np
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping
import os

MODEL_PATH = "app/ml/models/lstm_risk_model.h5"
WINDOW_SIZE = 10

class LSTMRiskProductionModel:

    def build(self):
        model = Sequential([
            LSTM(64, input_shape=(WINDOW_SIZE, 1)),
            Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")
        return model

    def train(self, risk_series: list):
        X, y = [], []
        for i in range(len(risk_series) - WINDOW_SIZE):
            X.append(risk_series[i:i+WINDOW_SIZE])
            y.append(risk_series[i+WINDOW_SIZE])

        X = np.array(X).reshape(-1, WINDOW_SIZE, 1)
        y = np.array(y)

        model = self.build()
        model.fit(
            X, y,
            epochs=50,
            batch_size=8,
            callbacks=[EarlyStopping(patience=5)],
            verbose=0
        )

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        model.save(MODEL_PATH)

    def predict(self, recent_risks: list) -> int:
        if not os.path.exists(MODEL_PATH):
            return recent_risks[-1]

        model = load_model(MODEL_PATH)
        X = np.array(recent_risks[-WINDOW_SIZE:]).reshape(1, WINDOW_SIZE, 1)
        pred = model.predict(X, verbose=0)[0][0]

        return max(0, min(int(pred), 100))
