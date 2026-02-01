import os
import pytest
from unittest.mock import patch

# Pre-set DATABASE_URL to avoid module-level crash during import
# This is required because app.core.config instantiates Settings() on import
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.config import Settings

def test_fallback_postgres_url():
    """
    Verifies that if DATABASE_URL is missing but POSTGRES_URL is present,
    DATABASE_URL is populated with the value of POSTGRES_URL.
    """
    # Setup environment: DATABASE_URL missing, POSTGRES_URL present
    env_vars = {
        "POSTGRES_URL": "postgresql://user:password@localhost:5432/dbname",
    }

    # Use patch.dict to modify os.environ temporarily
    with patch.dict(os.environ, env_vars):
        # Explicitly remove DATABASE_URL if it exists (from our pre-set)
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        # Instantiate Settings
        # This should succeed due to the fallback logic
        # Pass _env_file=None to ignore any local .env file
        settings = Settings(_env_file=None)

        assert settings.DATABASE_URL == "postgresql://user:password@localhost:5432/dbname"

def test_database_url_priority():
    """
    Verifies that if DATABASE_URL is present, it takes precedence over POSTGRES_URL.
    """
    env_vars = {
        "DATABASE_URL": "sqlite:///./priority.db",
        "POSTGRES_URL": "postgresql://ignore:me@localhost/db",
    }

    with patch.dict(os.environ, env_vars):
        settings = Settings(_env_file=None)
        # Should use the explicit DATABASE_URL
        assert settings.DATABASE_URL == "sqlite:///./priority.db"

def test_fallback_pg_variables():
    """
    Verifies that if DATABASE_URL and POSTGRES_URL are missing,
    but standard PG* variables are present, DATABASE_URL is constructed correctly.
    """
    env_vars = {
        "PGHOST": "db.railway.internal",
        "PGPORT": "5432",
        "PGUSER": "postgres",
        "PGPASSWORD": "secretpassword",
        "PGDATABASE": "railway",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        # Instantiate Settings
        settings = Settings(_env_file=None)

        expected_url = "postgresql://postgres:secretpassword@db.railway.internal:5432/railway"
        assert settings.DATABASE_URL == expected_url

def test_fallback_pg_variables_special_chars():
    """
    Verifies that special characters in the password are correctly URL-encoded.
    """
    env_vars = {
        "PGHOST": "db.railway.internal",
        "PGPORT": "5432",
        "PGUSER": "postgres",
        "PGPASSWORD": "pwd@#&%",
        "PGDATABASE": "railway",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings(_env_file=None)
        # pwd@#&% -> pwd%40%23%26%25
        expected_pwd = "pwd%40%23%26%25"
        expected_url = f"postgresql://postgres:{expected_pwd}@db.railway.internal:5432/railway"
        assert settings.DATABASE_URL == expected_url

def test_fallback_fail_if_missing_required():
    """
    Verifies that if DATABASE_URL is missing and insufficient PG vars are present,
    it raises a ValidationError (Field required).
    """
    env_vars = {
        "PGHOST": "db.railway.internal",
        # Missing others
    }

    with patch.dict(os.environ, env_vars, clear=True):
        with pytest.raises(ValueError): # Pydantic raises ValidationError which wraps ValueError
             Settings(_env_file=None)
