import sys
from unittest.mock import MagicMock
import os
import pytest

# Set environment variables for testing
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("AUTH_SECRET", "dummy")
os.environ.setdefault("GITHUB_CLIENT_ID", "dummy")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "dummy")

# Mock heavy dependencies
mock_tf = MagicMock()
sys.modules["tensorflow"] = mock_tf
sys.modules["tensorflow.keras"] = mock_tf.keras
sys.modules["tensorflow.keras.models"] = mock_tf.keras.models
sys.modules["tensorflow.keras.layers"] = mock_tf.keras.layers
sys.modules["tensorflow.keras.callbacks"] = mock_tf.keras.callbacks
