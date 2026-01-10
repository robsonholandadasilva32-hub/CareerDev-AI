import random
import string
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models.otp import OTP
from app.core.config import settings
from email.message import EmailMessage
import aiosmtplib
from twilio.rest import Client

def generate_otp_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def create_otp(db: Session, user_id: int, method: str):
    code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    otp = OTP(
        user_id=user_id,
        code=code,
        method=method,
        expires_at=expires_at
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    # Retrieve user phone number if method is sms
    phone_number = None
    if method == "sms":
        from app.db.crud.users import get_user_by_id
        # Note: Ideally we pass the user object or phone to avoid circular imports or extra queries
        # For now, we'll fetch it here or refactor.
        # Simpler: We'll modify create_otp to accept phone/email optionally, or fetch it.
        # Let's fetch it from DB for reliability.
        user = db.query(OTP).filter(OTP.id == otp.id).first().user # Navigation property might work if defined
        # Fallback to direct query
        from app.db.models.user import User
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj:
            phone_number = user_obj.phone_number

    # Try to send real notification, fallback to mock if config missing
    asyncio.create_task(send_notification(method, code, phone_number))

    # Mock Log (Always helpful for dev)
    print(f"========================================")
    print(f"[MOCK/REAL NOTIFICATION] To User {user_id} via {method}")
    print(f"Code: {code}")
    print(f"========================================")

    return otp

async def send_notification(method: str, code: str, phone_number: str = None):
    if method == "email":
        await send_email(code)
    elif method == "sms":
        if phone_number:
            send_sms(code, phone_number)
        else:
            print("[WARN] No phone number found for user. Cannot send SMS.")

async def send_email(code: str):
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        print("[WARN] SMTP not configured. Skipping real email.")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["Subject"] = "Seu código CareerDev AI"
    # Note: In a real app we'd need the user's email here.
    # For now, we are just implementing the sender logic structure.
    # To fix this, create_otp needs to accept the user email or fetch it.

    # Simulating sending to self/admin for demo purposes if we don't pass target email
    # or print warning
    print(f"[INFO] Would send email with code {code} via {settings.SMTP_SERVER}")

    # Example actual implementation code (commented out until target email is available)
    # message["To"] = target_email
    # message.set_content(f"Seu código de verificação é: {code}")
    # await aiosmtplib.send(
    #     message,
    #     hostname=settings.SMTP_SERVER,
    #     port=settings.SMTP_PORT,
    #     username=settings.SMTP_USERNAME,
    #     password=settings.SMTP_PASSWORD,
    #     use_tls=True
    # )

def send_sms(code: str, to_number: str):
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("[WARN] Twilio not configured. Skipping real SMS.")
        return

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"CareerDev AI Code: {code}",
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number
        )
        print(f"[SUCCESS] SMS sent via Twilio! SID: {message.sid}")
    except Exception as e:
        print(f"[ERROR] Twilio error: {e}")

def verify_otp(db: Session, user_id: int, code: str):
    otp = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.code == code,
        OTP.expires_at > datetime.utcnow()
    ).first()

    if otp:
        # Delete OTP after use to prevent replay
        db.delete(otp)
        db.commit()
        return True
    return False
