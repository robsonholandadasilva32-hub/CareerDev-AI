from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("careerdev_session")
    return response
