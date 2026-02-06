import sys
import os
from unittest.mock import MagicMock

# Set Env Vars BEFORE any imports to satisfy Pydantic Settings
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["GITHUB_CLIENT_ID"] = "dummy-client-id"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy-client-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "dummy-li-client-id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "dummy-li-client-secret"

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# MOCK HEAVY DEPENDENCIES
# We mock these to avoid installing them and to speed up tests.
# These are primarily used in ML services which are not the focus of this performance test.
module_names = [
    "tensorflow",
    "tensorflow.keras",
    "tensorflow.keras.models",
    "tensorflow.keras.layers",
    "tensorflow.keras.callbacks",
    "sklearn",
    "sklearn.linear_model",
    "pandas",
    "numpy",
    "joblib",
    "mlflow",
    "github",
    "cv2",
    "openai"
]

for module_name in module_names:
    sys.modules[module_name] = MagicMock()
