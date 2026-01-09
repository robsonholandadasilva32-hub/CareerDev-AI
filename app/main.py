from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from pathlib import Path

from app.db.base import Base
from app.db.session import engine
from app.routes import auth, dashboard, chatbot, security, email_verification, two_factor, logout

app = FastAPI(title="CareerDev AI")

# Database Creation
Base.metadata.create_all(bind=engine)

# Security Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] # Restrict this in production
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="a#j@dO6@6NA3qna1oa5hotn*%ndiTRX1285$x76h&ZsQN",
    session_cookie="careerdev_session",
    same_site="lax",
    https_only=False
)

# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/static/favicon/manifest.json")
def manifest():
    return FileResponse(
        Path("app/static/favicon/manifest.json"),
        media_type="application/manifest+json"
    )

@app.get("/sw.js")
def service_worker():
    return FileResponse(
        Path("app/static/sw.js"),
        media_type="application/javascript"
    )

# Routes
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(chatbot.router)
app.include_router(security.router)
app.include_router(email_verification.router)
app.include_router(two_factor.router)
app.include_router(logout.router)
