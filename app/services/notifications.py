import random
import string
import asyncio
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models.otp import OTP
from app.core.config import settings
from email.message import EmailMessage
from email.utils import formataddr
from jinja2 import Template
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

    # Retrieve user info
    from app.db.models.user import User
    user_obj = db.query(User).filter(User.id == user_id).first()

    phone_number = user_obj.phone_number if user_obj else None
    email = user_obj.email if user_obj else None

    # Try to send real notification, fallback to mock if config missing
    asyncio.create_task(send_notification(method, code, phone_number, email))

    # Mock Log (Always helpful for dev)
    print(f"========================================")
    print(f"[MOCK/REAL NOTIFICATION] To User {user_id} via {method}")
    print(f"Code: {code}")
    print(f"========================================")

    return otp

async def send_notification(method: str, code: str, phone_number: str = None, email: str = None):
    if method == "email":
        await send_email(code, email)
    elif method == "sms":
        if phone_number:
            send_sms(code, phone_number)
        else:
            print("[WARN] No phone number found for user. Cannot send SMS.")

async def send_email(code: str, to_email: str):
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        print("[WARN] SMTP not configured. Skipping real email.")
        return

    if not to_email:
        print("[WARN] No target email provided. Skipping.")
        return

    message = EmailMessage()
    message["From"] = formataddr(("CareerDev AI Security", settings.SMTP_FROM_EMAIL))
    message["To"] = to_email
    message["Subject"] = "Seu código de acesso | CareerDev AI"

    # Render HTML Template
    try:
        template_path = os.path.join(os.getcwd(), "app/templates/email/otp.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Simple Jinja2 rendering (or just replace if simple)
        # Using Jinja2 strictly if we had environment, but simple replace works for single var
        # To be robust, let's use Jinja2 Template class since we imported it
        template = Template(template_content)
        html_content = template.render(code=code)

        message.set_content(f"Seu código é: {code}") # Fallback text
        message.add_alternative(html_content, subtype='html')

    except Exception as e:
        print(f"[WARN] Failed to load email template: {e}. Sending plain text.")
        message.set_content(f"Seu código de verificação é: {code}")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_SERVER,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=False,
            start_tls=True
        )
        print(f"[SUCCESS] Email sent to {to_email}")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

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
