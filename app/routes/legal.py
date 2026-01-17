from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.i18n.loader import get_texts

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

SUPPORTED_LEGAL_LANGS = ["pt", "en", "es", "fr", "de"]

def get_legal_template(base_name: str, lang: str) -> str:
    # Normalize lang (e.g., pt-BR -> pt)
    simple_lang = lang.split("-")[0].lower()

    if simple_lang not in SUPPORTED_LEGAL_LANGS:
        simple_lang = "pt"

    return f"legal/{base_name}_{simple_lang}.html"

@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)
    template_name = get_legal_template("terms", lang)
    return templates.TemplateResponse(template_name, {"request": request, "t": t, "lang": lang})

@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)
    template_name = get_legal_template("privacy", lang)
    return templates.TemplateResponse(template_name, {"request": request, "t": t, "lang": lang})
