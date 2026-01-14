from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.i18n.loader import get_texts

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)
    return templates.TemplateResponse("terms.html", {"request": request, "t": t, "lang": lang})

@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)
    return templates.TemplateResponse("privacy.html", {"request": request, "t": t, "lang": lang})
