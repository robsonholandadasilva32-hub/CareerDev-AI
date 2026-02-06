import sys
from unittest.mock import MagicMock
import os

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["AUTH_SECRET"] = "dummy"
os.environ["GITHUB_CLIENT_ID"] = "dummy"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy"
os.environ["LINKEDIN_CLIENT_ID"] = "dummy"
os.environ["LINKEDIN_CLIENT_SECRET"] = "dummy"
os.environ["FORCE_COLOR"] = "1"

# Mock heavy dependencies
sys.modules["tensorflow"] = MagicMock()
sys.modules["tensorflow.keras"] = MagicMock()
sys.modules["tensorflow.keras.models"] = MagicMock()
sys.modules["tensorflow.keras.layers"] = MagicMock()
sys.modules["tensorflow.keras.callbacks"] = MagicMock()
sys.modules["tensorflow.keras.optimizers"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["sklearn.linear_model"] = MagicMock()
sys.modules["sklearn.ensemble"] = MagicMock()
sys.modules["mlflow"] = MagicMock()
