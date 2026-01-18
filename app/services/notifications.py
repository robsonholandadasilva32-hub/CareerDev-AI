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
from app.i18n.loader import get_texts
import logging

logger = logging.getLogger(__name__)

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
    lang = user_obj.preferred_language or "pt" if user_obj else "pt"

    # Add Job to DB (Robust Way)

    if method == "email":
        # Use template system for I18n
        payload = {
            "email": email,
            "template": "verification_code",
            "context": {"code": code},
            "lang": lang
        }
        task_type = "send_email_template"

    elif method == "telegram":
        payload = {'code': code, 'chat_id': phone_number}
        task_type = "send_telegram" # Keep using simple telegram for now or switch to template if key added

    job = BackgroundJob(task_type=task_type, payload=payload)
    db.add(job)
    db.commit()

    logger.info(f"JOB ENQUEUED: To User {user_id} via {method}")
    return otp

def enqueue_email(db: Session, user_id: int, template_name: str, context: dict):
    from app.db.models.user import User
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.email:
        logger.warning(f"Cannot enqueue email: User {user_id} not found or no email.")
        return

    # Add localized user name if not present
    if "user_name" not in context:
        context["user_name"] = user.name

    payload = {
        "email": user.email,
        "template": template_name,
        "context": context,
        "lang": user.preferred_language or "pt"
    }

    job = BackgroundJob(task_type="send_email_template", payload=payload)
    db.add(job)
    db.commit()
    logger.info(f"JOB ENQUEUED: Email '{template_name}' to {user.email}")

def enqueue_raw_email(db: Session, to_email: str, subject: str, body: str):
    """Enqueues a raw email (no template) for support/system messages."""
    payload = {
        "to_email": to_email,
        "subject": subject,
        "body": body
    }
    job = BackgroundJob(task_type="send_raw_email", payload=payload)
    db.add(job)
    db.commit()
    logger.info(f"JOB ENQUEUED: Raw Email to {to_email}")

def enqueue_telegram(db: Session, user_id: int, template_key: str, context: dict):
    from app.db.models.user import User
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.phone_number:
        # User might not have Telegram set up or has SMS as fallback
        return

    # Only send if they explicitly chose Telegram as their method.
    # We strictly check for 'telegram' here to avoid sending API requests to SMS numbers.
    if user.two_factor_method != "telegram":
        return

    if "user_name" not in context:
        context["user_name"] = user.name

    payload = {
        "chat_id": user.phone_number,
        "template_key": template_key,
        "context": context,
        "lang": user.preferred_language or "pt"
    }

    job = BackgroundJob(task_type="send_telegram_template", payload=payload)
    db.add(job)
    db.commit()
    logger.info(f"JOB ENQUEUED: Telegram '{template_key}' to {user.phone_number}")

# Global Jinja2 Environment for caching and security
_jinja_env = None

def get_jinja_env():
    global _jinja_env
    if _jinja_env is None:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        _jinja_env = Environment(
            loader=FileSystemLoader("app/templates"),
            autoescape=select_autoescape(['html', 'xml'])
        )
    return _jinja_env

# --- ROBUST EMAIL SENDING HELPER ---
async def _send_smtp_message(message: EmailMessage, to_email: str):
    """Helper to send email with robust configuration (TLS/SSL/Timeout)."""
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_SERVER,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,       # Configurable Implicit TLS
            start_tls=settings.SMTP_USE_STARTTLS, # Configurable STARTTLS
            timeout=settings.SMTP_TIMEOUT        # Configurable Timeout
        )
        logger.info(f"SUCCESS: Email sent to {to_email}")
        return True
    except asyncio.TimeoutError:
        logger.error(f"TIMEOUT: Failed to send email to {to_email} within {settings.SMTP_TIMEOUT}s")
        raise # Let worker handle retry
    except Exception as e:
        logger.error(f"SMTP ERROR: Failed to send email to {to_email}: {e}")
        raise

async def send_email_template(to_email: str, template_name: str, context: dict, lang: str = "pt"):
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        logger.warning("SMTP not configured. Skipping real email.")
        return

    t = get_texts(lang)

    try:
        env = get_jinja_env()
        template = env.get_template(f"email/{template_name}.html")

        # Inject translations
        full_context = {**context, "t": t, "lang": lang}
        html_content = template.render(**full_context)

        # Determine subject based on template or key
        subject_key = f"email_{template_name}_subject"
        subject = t.get(subject_key, "CareerDev AI Notification")

        message = EmailMessage()
        message["From"] = formataddr(("CareerDev AI", settings.SMTP_FROM_EMAIL))
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content("Please enable HTML to view this email.")
        message.add_alternative(html_content, subtype='html')

        await _send_smtp_message(message, to_email)

    except Exception as e:
        logger.error(f"Failed to process email template '{template_name}': {e}")
        # If it's a template error, don't retry. If it's network (from _send), it raised already.
        if "SMTP ERROR" in str(e) or "TIMEOUT" in str(e):
             raise e

async def send_raw_email(to_email: str, subject: str, body: str):
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        logger.warning("SMTP not configured. Skipping real email.")
        return

    try:
        message = EmailMessage()
        message["From"] = formataddr(("CareerDev AI Support", settings.SMTP_FROM_EMAIL))
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        await _send_smtp_message(message, to_email)

    except Exception as e:
        logger.error(f"Failed to process raw email: {e}")
        if "SMTP ERROR" in str(e) or "TIMEOUT" in str(e):
             raise e

async def send_raw_email(to_email: str, subject: str, body: str):
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        logger.warning("SMTP not configured. Skipping real email.")
        return

    try:
        message = EmailMessage()
        message["From"] = formataddr(("CareerDev AI Support", settings.SMTP_FROM_EMAIL))
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_SERVER,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=False,
            start_tls=True
        )
        logger.info(f"SUCCESS: Raw Email sent to {to_email}")

    except Exception as e:
        logger.error(f"Failed to send raw email: {e}")

async def send_notification(method: str, code: str, phone_number: str = None, email: str = None):
    # This function is largely deprecated by create_otp using jobs directly,
    # but kept if used elsewhere.
    if method == "email":
        await send_email(code, email)
    elif method == "telegram" or method == "sms": # Handle 'sms' legacy as telegram
        if phone_number:
            await send_telegram(code, phone_number)
        else:
            logger.warning("No Telegram Chat ID found for user.")

async def send_email(code: str, to_email: str):
    # DEPRECATED: Use send_email_template
    # Kept for backward compatibility but updated to use robust sender
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        logger.warning("SMTP not configured. Skipping real email.")
        return
        logger.warning("SMTP not configured. Skipping real email.")
        return

    if not to_email:
        logger.warning("No target email provided. Skipping.")
        return

    message = EmailMessage()
    message["From"] = formataddr(("CareerDev AI Security", settings.SMTP_FROM_EMAIL))
    message["To"] = to_email
    message["Subject"] = "Seu código de acesso | CareerDev AI"

    try:
        # Fallback to old template if exists, or just verify code template
        template_path = os.path.join(os.getcwd(), "app/templates/email/otp.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
            template = Template(template_content)
            html_content = template.render(code=code)
            message.set_content(f"Seu código é: {code}")
            message.add_alternative(html_content, subtype='html')
        else:
             message.set_content(f"Seu código de verificação é: {code}")

    except Exception as e:
        logger.warning(f"Failed to load email template: {e}. Sending plain text.")
        message.set_content(f"Seu código de verificação é: {code}")

    try:
        await _send_smtp_message(message, to_email)
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

async def send_telegram(code: str, chat_id: str):
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram Bot Token not configured. Skipping real message.")
        return

    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        message = f"🔒 *CareerDev AI* \n\nSeu código de segurança: `{code}`\n\nVálido por 10 minutos."
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logger.info(f"SUCCESS: Telegram message sent to {chat_id}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

async def send_telegram_template(chat_id: str, template_key: str, context: dict, lang: str = "pt"):
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram Bot Token not configured. Skipping real message.")
        return

    t = get_texts(lang)
    message_template = t.get(template_key, "")

    if not message_template:
        logger.warning(f"Telegram template '{template_key}' not found.")
        return

    # Replace placeholders with markdown escaping
    for key, value in context.items():
        # Escape markdown special characters in values (MarkdownV2)
        val_str = str(value)
        # Escape backslash first to avoid double escaping
        val_str = val_str.replace("\\", "\\\\")
        escape_chars = r"_*[]()~`>#+-=|{}.!"
        for char in escape_chars:
            val_str = val_str.replace(char, f"\\{char}")

        message_template = message_template.replace(f"{{{{{key}}}}}", val_str)

    # Add footer if not already in template (simple consistency check)
    if "CareerDev AI" not in message_template:
        message_template += "\n\n_Sent via CareerDev AI_"

    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=message_template, parse_mode="MarkdownV2")
        logger.info(f"SUCCESS: Telegram template '{template_key}' sent to {chat_id}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")


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
