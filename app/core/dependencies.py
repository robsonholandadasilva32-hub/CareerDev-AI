from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.jwt import decode_token
from app.db.models.user import User

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Decodes the JWT token from cookies and retrieves the user from the database.
    """
    token = request.cookies.get("access_token")
    if not token:
        # Redirect is usually handled by the route or middleware, but for a dependency,
        # we raise an exception which can be caught.
        # However, for simplicity in this project structure:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
