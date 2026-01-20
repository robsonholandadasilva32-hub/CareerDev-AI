import asyncio
import sys
import os

# Add the root directory to sys.path
sys.path.append(os.getcwd())

from app.services.notifications import send_raw_email

async def main():
    print("Attempting to send test email via aiosmtplib (Async)...")
    target_email = "admin@careerdev-ai.online"
    subject = "Teste de Envio Assíncrono - CareerDev AI"
    body = "Este é um teste para validar o envio de e-mail via aiosmtplib."

    try:
        await send_raw_email(target_email, subject, body)
        print("Email sent successfully (function returned).")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    asyncio.run(main())
