import asyncio
import sys
import os

# Add the root directory to sys.path
sys.path.append(os.getcwd())

from app.services.notifications import send_email

async def main():
    print("Attempting to send test email via SendGrid...")
    # Send to the same address as sender for testing to ensure delivery
    target_email = "robsonholandasilva@yahoo.com.br"
    await send_email("123456", target_email)

if __name__ == "__main__":
    asyncio.run(main())
