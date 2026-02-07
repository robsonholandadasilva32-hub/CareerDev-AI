# CareerDev AI
![License](https://img.shields.io/badge/License-Apache_2.0-green?style=flat)

**The AI-powered career prosperity platform.**

It combines machine precision with human intuition to optimize resumes and career strategies.

**Stack:** Python/FastAPI, Stripe, OAuth.

## 🚀 Features

*   **AI Resume Analysis:** Uses OpenAI to analyze resumes against target roles, identifying skill gaps.
*   **Security First:**
    *   Secure Session Management (HttpOnly, SameSite).
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

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

---
*Built with ❤️ for Developers.*
<!-- Force Rebuild: Tue Jan 20 19:57:32 UTC 2026 -->
