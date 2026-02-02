from fastapi.testclient import TestClient
from app.main import app
from app.routes.admin import get_current_super_admin
from app.db.models.user import User
from app.db.base import Base
from app.db.session import engine, get_db, SessionLocal
import pytest

# Create tables
Base.metadata.create_all(bind=engine)

def mock_super_admin():
    return User(id=1, email="robsonholandasilva@yahoo.com.br", is_admin=True, full_name="Super Admin")

def test_analytics_access_allowed_for_super_admin():
    # Override dependency
    app.dependency_overrides[get_current_super_admin] = mock_super_admin
    client = TestClient(app)

    response = client.get("/admin/analytics")
    assert response.status_code == 200
    assert "Data Analytics" in response.text

    # Clean up
    app.dependency_overrides = {}

def test_export_access_allowed_for_super_admin():
    app.dependency_overrides[get_current_super_admin] = mock_super_admin
    client = TestClient(app)

    response = client.get("/admin/analytics/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    app.dependency_overrides = {}
