from fastapi.templating import Jinja2Templates
from app.core.config import settings

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["model_name"] = settings.LLM_MODEL_DISPLAY_NAME
