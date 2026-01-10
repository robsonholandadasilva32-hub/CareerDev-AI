# Test script for SMS sending logic
import sys
import os

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notifications import send_sms
from app.core.config import settings

def test_sms_config():
    print("Testing Twilio Configuration...")
    print(f"SID Configured: {'Yes' if settings.TWILIO_ACCOUNT_SID else 'No'}")
    print(f"Token Configured: {'Yes' if settings.TWILIO_AUTH_TOKEN else 'No'}")
    print(f"From Number: {settings.TWILIO_FROM_NUMBER}")

    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("FAIL: Twilio credentials missing.")
        return

    # Simulate sending (we can't actually send without a destination number provided by user)
    # The user provided credentials but not a destination number in the chat.
    # However, the code logic is what we are testing here.

    print("\n[MOCK TEST] calling send_sms with a dummy number...")
    # This might fail if Twilio validates the number format or if it's not a verified caller ID (if in trial mode)
    # But it verifies the library is loaded and auth is attempted.
    try:
        # Using a magic number for testing if available or just a placeholder
        send_sms("123456", "+15005550006") # Twilio Test Number (Magic number that passes validation)
    except Exception as e:
        print(f"Result: {e}")

if __name__ == "__main__":
    test_sms_config()
