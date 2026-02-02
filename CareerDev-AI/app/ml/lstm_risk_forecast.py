import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

class LSTMRiskModel:
    def build(self):
        model = Sequential([
            LSTM(64, input_shape=(10, 1)),
            Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")
        return model
