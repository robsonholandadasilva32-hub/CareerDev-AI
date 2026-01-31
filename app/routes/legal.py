from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.templates import templates

router = APIRouter()

# Mantendo a função auxiliar da branch main
def get_legal_template(base_name: str) -> str:
    return f"legal/{base_name}.html"

@router.get("/", response_class=HTMLResponse)
def legal_menu(request: Request):
    # This route is protected by AuthMiddleware usually if it were under /dashboard,
    # but since it's now /legal, we might want to check for user presence if we want to enforce login for the menu.
    # However, the requirement was to make the hierarchy flattened.
    # Assuming AuthMiddleware doesn't block /legal automatically unless configured.
    # But usually dashboard menu items imply logged in state.
    # If the user is not logged in, they might see a broken page if it extends dashboard_layout.
    # Let's check if request.state.user is present.
    user = getattr(request.state, "user", None)
    if not user:
         from fastapi.responses import RedirectResponse
         return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse("legal_menu.html", {"request": request, "user": user})

@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse("legal/terms.html", {"request": request})

@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse("legal/privacy.html", {"request": request})