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
from pathlib import Path
from dotenv import load_dotenv

# 1. Carregar .env e Configurar Logs
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. CAMINHO ABSOLUTO (Correção importante para o PythonAnywhere)
BASE_DIR = Path(__file__).resolve().parent

# 3. IMPORTAÇÕES SEM PROTEÇÃO (Para descobrirmos o erro real)
# Se faltar alguma biblioteca aqui, o erro vai aparecer no Log de Erros.
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.config import settings
from app.services.gamification import init_badges

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

    except Exception as e:
        logger.error(f"ERRO CRITICO NO BANCO: {e}")
        # Não queremos que o app inicie se o banco falhar
        raise e
    yield
    logger.info("Desligando...")

# 5. Inicialização do App
app = FastAPI(title="CareerDev AI", lifespan=lifespan)

# 5.5 Exception Handlers
templates = Jinja2Templates(directory="app/templates")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request, "t": {}, "lang": "pt"}, status_code=404)

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request, "t": {}, "lang": "pt"}, status_code=500)

# 6. Middlewares
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="careerdev_session",
    same_site="lax",
    https_only=False, # Set to True in production with env var check
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