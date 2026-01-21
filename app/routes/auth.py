from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.i18n.loader import get_texts
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# =====================================================
# LOGIN PAGE (GET)
# =====================================================
@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    lang = request.query_params.get("lang")

    if lang not in ("pt", "en", "es", "fr", "de"):
        lang = request.session.get("lang", "pt")

    request.session["lang"] = lang
    t = get_texts(lang)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "lang": lang,
            "t": t
        }
    )
