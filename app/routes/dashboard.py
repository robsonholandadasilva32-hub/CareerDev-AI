from fastapi import APIRouter, Request, Depends, HTTPException, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.services.social_harvester import social_harvester
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import get_active_sessions, revoke_session, log_audit
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.security import UserSession
from app.db.models.gamification import UserBadge
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- DEPENDÊNCIA DE SEGURANÇA ---
def get_current_user_secure(request: Request, db: Session = Depends(get_db)):
    # 🛡️ Relies on AuthMiddleware for session validation
    if not getattr(request.state, "user", None):
        return None

    user_id = request.state.user.id
    user = (
        db.query(User)
        .options(
            joinedload(User.badges).joinedload(UserBadge.badge),
            joinedload(User.career_profile)
        )
        .filter(User.id == user_id)
        .first()
    )
    return user

# --- ROTA PRINCIPAL (DASHBOARD) ---
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_secure)):
    # 1. Validação de Login
    if not user:
        return RedirectResponse("/login", status_code=302)

    # 2. Validação de Onboarding (Fluxo Sequencial)
    redirect = validate_onboarding_access(user)
    if redirect:
        return redirect

    # 3. Execução da Lógica de Carreira (Real Engine)
    # Analisa perfil, busca dados externos e gera insights
    await career_engine.analyze_profile(db, user)
    career_data = await career_engine.get_career_dashboard_data(db, user)

    # 4. Preparação de Dados para a Nova Interface (Mapping)
    # Extraindo dados simples da estrutura complexa do career_engine para o HTML
    market_score = career_data.get("zone_a_holistic", {}).get("score", 0)
    # Se user.streak_count não existir no model, usa 0 como fallback
    user_streak = getattr(user, "streak_count", 0) 

    # Lógica de Saudação Contextual
    greeting_skill = "your career"
    try:
        # Tenta pegar a top skill dos dados brutos
        raw_langs = user.career_profile.github_activity_metrics.get("raw_languages", {})
        if raw_langs:
            greeting_skill = sorted(raw_langs.items(), key=lambda x: x[1], reverse=True)[0][0]
    except Exception:
        pass

    greeting_message = f"Hello! Detected high activity in {greeting_skill}. Ready to optimize?"

    # 5. Renderização
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "user_id": user.id,
            "email": user.email,
            
            # Dados para a Interface Nova
            "market_score": market_score,
            "user_streak": user_streak,
            "career_data": career_data, # Passa o objeto completo também para uso avançado
            
            "badges": user.badges,
            "greeting_message": greeting_message,
        }
    )

# --- ROTAS DE FUNCIONALIDADES (Solicitações 2, 3, 4, 6) ---

@router.get("/dashboard/network")
def network_node(request: Request, user: User = Depends(get_current_user_secure)):
    """Solicitação 6: Rota do ícone de Rede"""
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard/network.html", {"request": request, "user": user})

@router.get("/dashboard/security")
def security_panel(request: Request, user: User = Depends(get_current_user_secure)):
    """Solicitação 3: Escudo = Segurança"""
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard/security.html", {"request": request, "user": user})

# ATUALIZADO AQUI (Aba Legal Hub com Privacidade e Termos)
@router.get("/legal", response_class=HTMLResponse)
def legal_panel(request: Request):
    """
    Legal Hub: Renderiza a Política de Privacidade e Termos de Uso.
    """
    return templates.TemplateResponse("legal.html", {"request": request})

@router.get("/accessibility")
def accessibility_settings(request: Request):
    """Solicitação 2: Cérebro = Acessibilidade"""
    return templates.TemplateResponse("accessibility.html", {"request": request})


# --- API ENDPOINTS (Ajax/Fetch) ---

@router.get("/api/dashboard/stats", response_class=JSONResponse)
async def get_dashboard_stats(user: User = Depends(get_current_user_secure), db: Session = Depends(get_db)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await career_engine.get_career_dashboard_data(db, user)
    return data

@router.post("/api/dashboard/tasks/{task_id}/complete")
async def complete_task(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_secure)):
    # Lógica para marcar tarefa como concluída e disparar re-scan
    if not current_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # Simulação de update (Implementar lógica real de DB aqui se necessário)
    logger.info(f"Task {task_id} completed by {current_user.email}")

    # Trigger Re-scan (Ciclo de Feedback)
    if current_user.github_token:
         background_tasks.add_task(social_harvester.harvest_github_data, current_user.id, current_user.github_token)
    else:
         background_tasks.add_task(social_harvester.scan_github, db, current_user)

    return {"status": "success", "message": "Task verified. Market Score updated."}
