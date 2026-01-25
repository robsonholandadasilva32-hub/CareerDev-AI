from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Mantendo a função auxiliar da branch main
def get_legal_template(base_name: str) -> str:
    return f"legal/{base_name}.html"

@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse("legal/terms.html", {"request": request})

@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse("legal/privacy.html", {"request": request})

@router.get("/security-accessibility", response_class=HTMLResponse)
def security_accessibility_page(request: Request):
    return templates.TemplateResponse("legal/security_accessibility.html", {"request": request})