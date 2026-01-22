from fastapi import Request, HTTPException, status
from app.core.exceptions import PremiumRedirect

async def requires_premium_tier(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        # If not logged in, we raise 401. The global handler or client should handle it.
        # Ideally this dependency is used after authentication.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not user.is_premium:
        raise PremiumRedirect()

    return user
