import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter
from pathlib import Path
from dotenv import load_dotenv
import sentry_sdk

# 1. Carregar .env e Configurar Logs
load_dotenv()

# Structured Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval';"
        return response

# Initialize Sentry (if DSN provided)
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# 2. CAMINHO ABSOLUTO (Correção importante para o PythonAnywhere)
BASE_DIR = Path(__file__).resolve().parent

# 3. IMPORTAÇÕES SEM PROTEÇÃO (Para descobrirmos o erro real)
# Se faltar alguma biblioteca aqui, o erro vai aparecer no Log de Erros.
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.config import settings
from app.services.gamification import init_badges
from app.services.worker import job_worker

# Importando suas rotas
from app.routes import (
    auth, dashboard, chatbot, security,
    email_verification, two_factor, logout, social, billing, career, legal
)

# 4. Lifespan (Conexão com Banco)
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Criando tabelas no banco de dados...")
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados pronto!")

        # Initialize Badges
        db = SessionLocal()
        try:
            init_badges(db)
            logger.info("Badges inicializados.")
        finally:
            db.close()

        # Start Background Worker
        job_worker.start()

    except Exception as e:
        logger.error(f"ERRO CRITICO NO BANCO: {e}")
        # Não queremos que o app inicie se o banco falhar
        raise e
    yield
    logger.info("Desligando...")
    job_worker.stop()

# 5. Inicialização do App
app = FastAPI(title="CareerDev AI", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 5.5 Exception Handlers
templates = Jinja2Templates(directory="app/templates")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request, "t": {}, "lang": "pt"}, status_code=404)

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request, "t": {}, "lang": "pt"}, status_code=500)

# 6. Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"]) # Review allow_hosts for production!
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS (Configured for Production Safety)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","), # Use env var in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="careerdev_session",
    same_site="lax",
    https_only=os.getenv("Render", "False") == "True" or os.getenv("DYNO") is not None, # Auto-detect prod envs (Render/Heroku)
    max_age=1800 # 30 minutes session invalidation
)

# 7. Arquivos Estáticos (Com caminho absoluto corrigido)
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 8. Rota Principal
@app.get("/")
def root():
    return RedirectResponse("/login")

@app.get("/static/favicon/manifest.json")
def manifest():
    manifest_path = static_dir / "favicon" / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return JSONResponse({"error": "Manifest not found"}, status_code=404)

# 9. Inclusão de Rotas
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(chatbot.router, prefix="/chatbot")
app.include_router(security.router)
app.include_router(email_verification.router)
app.include_router(two_factor.router)
app.include_router(logout.router)
app.include_router(social.router)
app.include_router(billing.router)
app.include_router(career.router, prefix="/career")
app.include_router(legal.router, prefix="/legal")