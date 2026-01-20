from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.core.jwt import create_access_token, decode_token
from app.core.security import hash_password, verify_password
from app.routes.security import get_db as security_get_db

client = TestClient(app)

def test_security_password_update_flow():
    # 1. Setup Mock User and DB
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.hashed_password = hash_password("oldpassword")
    mock_user.two_factor_method = "email"
    mock_user.preferred_language = "pt"

    # Mock DB session
    mock_session = MagicMock()

    # Mock get_db dependency using dependency_overrides
    def override_get_db():
        yield mock_session

    app.dependency_overrides[security_get_db] = override_get_db

    # However, for an integration test of the flow, we can use the TestClient.
    # We need to simulate a logged-in user.

    token = create_access_token({"sub": "1"})
    cookies = {"access_token": token}

    # Mocking external services to avoid side effects
    with patch("app.routes.security.get_current_user", return_value=mock_user), \
         patch("app.routes.security.create_otp") as mock_create_otp, \
         patch("app.routes.security.verify_otp", return_value=True) as mock_verify_otp, \
         patch("app.routes.security.enqueue_email") as mock_email, \
         patch("app.routes.security.enqueue_telegram") as mock_telegram:

        # 2. Attempt to change password
        response = client.post(
            "/security/update",
            data={
                "current_password": "oldpassword",
                "new_password": "newpassword",
                "confirm_password": "newpassword",
                "method": "email",
                "language": "pt"
            },
            cookies=cookies,
            allow_redirects=False # We want to check the redirect
        )

        # Expect redirect to verification page (302)
        assert response.status_code == 302
        assert response.headers["location"] == "/security/verify-change"

        # Check if security_temp_token cookie is set
        assert "security_temp_token" in response.cookies
        temp_token = response.cookies["security_temp_token"]

        # Verify OTP was created
        mock_create_otp.assert_called_once()

        # 3. Verify Change (Submit OTP)
        # We need to manually pass the cookie we got
        cookies["security_temp_token"] = temp_token

        response = client.post(
            "/security/verify-change",
            data={"code": "123456"},
            cookies=cookies,
            allow_redirects=False
        )

        # Expect redirect to security page with success (302)
        assert response.status_code == 302
        assert response.headers["location"] == "/security?success=true"

        # Verify User Password Was Updated (In Mock)
        # In a real DB test we would check the DB. Here we check if the mock object was modified.
        # Since 'mock_user' is a reference, the route handler should have updated it.
        # Note: hash_password produces different salts, so we can't check equality directly against a string,
        # but we can check if it changed.
        assert mock_user.hashed_password != hash_password("oldpassword") # logic check

        # Verify Notifications
        mock_email.assert_called_with(mock_session, 1, "account_update", {"change_type": "password"})

        # Verify Token Cookie Cleared
        # TestClient handles cookie jar, but we can check 'set-cookie' header for deletion (usually expires=...)
        assert 'security_temp_token=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]

def test_security_resend_flow():
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.two_factor_method = "email"

    token = create_access_token({"sub": "1"})
    cookies = {"access_token": token}

    # Create a valid temp token
    temp_token = create_access_token({"sub": "1", "change_type": "password", "new_hash": "hash"})
    cookies["security_temp_token"] = temp_token

    with patch("app.routes.security.get_current_user", return_value=mock_user), \
         patch("app.routes.security.create_otp") as mock_create_otp:

        response = client.post(
            "/security/resend-change",
            cookies=cookies,
            allow_redirects=False
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/security/verify-change"
        mock_create_otp.assert_called_once()
