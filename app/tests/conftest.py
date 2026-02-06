import sys
import os
from unittest.mock import MagicMock
import pytest

# Set required environment variables BEFORE importing app code
# Usamos a configuração da main pois ela define chaves para LinkedIn e GitHub,
# evitando erros de KeyErrors nos testes de integração.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "test-client-id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "test-client-secret"
os.environ["GITHUB_CLIENT_ID"] = "test-github-id"
os.environ["GITHUB_CLIENT_SECRET"] = "test-github-secret"

# List of modules to mock
# A lista abrangente da main é essencial para performance.
# Ela evita o carregamento real de Data Science stack (Pandas, Numpy, etc),
# garantindo que os testes unitários sejam instantâneos.
MOCK_MODULES = [
    "tensorflow",
    "tensorflow.keras",
    "tensorflow.keras.models",
    "tensorflow.keras.layers",
    "tensorflow.keras.callbacks",
    "pandas",
    "sklearn",
    "sklearn.linear_model",
    "joblib",
    "openai",
    "numpy",
    "mlflow",
    "github",
]

# Apply mocks to sys.modules
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MagicMock()