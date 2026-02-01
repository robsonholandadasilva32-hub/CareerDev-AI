from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Dependências de autenticação e banco de dados
from app.api.deps import get_db  # Ajuste conforme sua estrutura de injeção de dependência
from app.routes.dashboard import get_current_user_secure
from app.services.career_engine import career_engine

router = APIRouter()

# =========================================================
# RISK EXPLAINABILITY (XAI)
# =========================================================
@router.get("/api/risk/explain")
async def explain_risk(
    user=Depends(get_current_user_secure)
):
    """
    Retorna a explicação textual (human-readable) dos fatores de risco.
    Alimenta o modal 'Why am I at risk?'.
    """
    return career_engine.explain_risk(user)

# =========================================================
# COUNTERFACTUAL ANALYSIS (WHAT-IF)
# =========================================================
@router.get("/api/risk/counterfactual")
async def counterfactual(
    db: Session = Depends(get_db), 
    user=Depends(get_current_user_secure)
):
    """
    Gera cenários alternativos: 'O que aconteceria com meu risco se...'
    Retorna sugestões acionáveis para reduzir o score de risco.
    """
    # Nota: Certifique-se de que o método 'get_counterfactual' 
    # foi implementado ou exposto no CareerEngine.
    # Caso contrário, você pode reutilizar a lógica interna do método 'analyze'.
    return career_engine.get_counterfactual(db, user)
