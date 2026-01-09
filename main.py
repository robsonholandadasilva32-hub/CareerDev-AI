from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
from app.routes import auth, dashboard, chatbot
from starlette.middleware.sessions import SessionMiddleware

from fastapi.staticfiles import StaticFiles

from app.routes.auth import router as auth_router


app = FastAPI(title="CareerDev AI")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)

app.add_middleware(
    SessionMiddleware,
    secret_key="careerdev-ai-secret-key",
    session_cookie="careerdev_session",
    same_site="lax",
    https_only=False
)

# Arquivos estáticos (CSS, JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

from fastapi.responses import FileResponse
from pathlib import Path

@app.get("/static/favicon/manifest.json")
def manifest():
    return FileResponse(
        Path("app/static/favicon/manifest.json"),
        media_type="application/manifest+json"
    )
 
# Rotas
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(chatbot.router)

from app.routes import security
app.include_router(security.router)

from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key="a#j@dO6@6NA3qna1oa5hotn*%ndiTRX1285$x76h&ZsQN"
)

from app.routes import email_verification
app.include_router(email_verification.router)

