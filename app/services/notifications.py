import random
import string
import asyncio
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models.otp import OTP
from app.db.models.job import BackgroundJob
from app.core.config import settings
from email.message import EmailMessage
from email.utils import formataddr
from jinja2 import Template
import aiosmtplib
from telegram import Bot

def generate_otp_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def create_otp(db: Session, user_id: int, method: str):
    code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Force method normalization just in case
    if method == "sms": method = "telegram"

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

    phone_number = user_obj.phone_number if user_obj else None # Used as Chat ID
    email = user_obj.email if user_obj else None

    # Add Job to DB (Robust Way)
    payload = {'code': code}
    task_type = "send_email"

    if method == "email":
        payload['email'] = email
        task_type = "send_email"
    elif method == "telegram":
        payload['chat_id'] = phone_number
        task_type = "send_telegram"

    job = BackgroundJob(task_type=task_type, payload=payload)
    db.add(job)
    db.commit()

    # Mock Log (Always helpful for dev)
    print(f"========================================")
    print(f"[JOB ENQUEUED] To User {user_id} via {method} | Code: {code}")
    print(f"========================================")

    return otp

async def send_notification(method: str, code: str, phone_number: str = None, email: str = None):
    if method == "email":
        await send_email(code, email)
    elif method == "telegram" or method == "sms": # Handle 'sms' legacy as telegram
        if phone_number:
            await send_telegram(code, phone_number)
        else:
            print("[WARN] No Telegram Chat ID found for user.")

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

    try:
        template_path = os.path.join(os.getcwd(), "app/templates/email/otp.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        template = Template(template_content)
        html_content = template.render(code=code)

        message.set_content(f"Seu código é: {code}")
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

async def send_telegram(code: str, chat_id: str):
    if not settings.TELEGRAM_BOT_TOKEN:
        print("[WARN] Telegram Bot Token not configured. Skipping real message.")
        return

    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        message = f"🔒 *CareerDev AI* \n\nSeu código de segurança: `{code}`\n\nVálido por 10 minutos."
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        print(f"[SUCCESS] Telegram message sent to {chat_id}")
    except Exception as e:
        print(f"[ERROR] Telegram error: {e}")

def verify_otp(db: Session, user_id: int, code: str):
    otp = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.code == code,
        OTP.expires_at > datetime.utcnow()
    ).first()

    if otp:
        db.delete(otp)
        db.commit()
        return True
    return False
