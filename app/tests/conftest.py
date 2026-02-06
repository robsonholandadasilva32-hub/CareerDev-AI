import sys
import os
from unittest.mock import MagicMock

# Set required environment variables BEFORE importing app code
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "test-client-id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "test-client-secret"
os.environ["GITHUB_CLIENT_ID"] = "test-github-id"
os.environ["GITHUB_CLIENT_SECRET"] = "test-github-secret"

# List of modules to mock
MOCK_MODULES = [
]

# Apply mocks to sys.modules
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MagicMock()
