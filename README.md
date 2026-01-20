# CareerDev AI

**CareerDev AI** is a high-performance, AI-powered career management platform for developers. Built with **FastAPI** and **Python 3.12**, it prioritizes security, accessibility, and professional growth.

## 🚀 Features

*   **AI Resume Analysis:** Uses OpenAI to analyze resumes against target roles, identifying skill gaps.
*   **Automated Notifications:** Professional email and Telegram notifications for account security and updates.
*   **Security First:**
    *   Secure Session Management (HttpOnly, SameSite).
    *   2FA Support (Email & Telegram).
    *   Security Headers (CSP, HSTS).
    *   Strict Rate Limiting.
*   **Accessibility:** WCAG-compliant design with themes for dyslexia, color blindness, and motor impairments.
*   **Gamification:** Earn badges for career milestones.
*   **Subscription System:** Stripe integration for premium features.

## 🛠️ Tech Stack

*   **Framework:** FastAPI (Python 3.12)
*   **Server:** Uvicorn (Production-ready with workers)
*   **Database:** SQLAlchemy + SQLite (Dev) / PostgreSQL (Prod)
*   **Migrations:** Alembic
*   **Tasks:** Custom Background Worker
*   **Templating:** Jinja2

## ⚙️ Configuration (Environment Variables)

Create a `.env` file in the root directory with the following keys:

```bash
# Application
SECRET_KEY=your_secure_secret
SESSION_SECRET_KEY=your_session_secret
DATABASE_URL=sqlite:///./careerdev.db

# Email (SMTP)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=noreply@careerdev.ai

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token

# AI (OpenAI)
OPENAI_API_KEY=sk-...

# Payments (Stripe)
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLISHABLE_KEY=pk_...

# Social Auth
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...

# Optional
SENTRY_DSN=...
ALLOWED_ORIGINS=https://yourdomain.com
```

## 📦 Installation & Running

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Migrations:**
    ```bash
    alembic upgrade head
    ```

3.  **Start Server:**
    ```bash
    # Development
    uvicorn app.main:app --reload

    # Production (or use start.sh)
    ./start.sh
    ```

## 🛡️ Deployment

The project is configured for secure deployment:
*   `runtime.txt` specifies Python 3.12.1.
*   `requirements.txt` has pinned versions.
*   `start.sh` uses multiple workers.
*   Security middleware is active by default.

---
*Built with ❤️ for Developers.*
<!-- Force Rebuild: Tue Jan 20 19:57:32 UTC 2026 -->
