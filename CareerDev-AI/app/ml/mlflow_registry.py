import mlflow

def register(model, version):
    mlflow.start_run()
    mlflow.log_param("version", version)
    mlflow.sklearn.log_model(model, "risk_model")
    mlflow.end_run()
