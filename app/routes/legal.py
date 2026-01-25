from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_legal_template(base_name: str) -> str:
    return f"legal/{base_name}.html"

@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    template_name = get_legal_template("terms")
    return templates.TemplateResponse(template_name, {"request": request})

@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    template_name = get_legal_template("privacy")
    return templates.TemplateResponse(template_name, {"request": request})
