from app.ml.risk_forecast_model import RiskForecastModel

def retrain():
    model = RiskForecastModel()
    model.train("career_training_dataset.csv", advanced=True)
