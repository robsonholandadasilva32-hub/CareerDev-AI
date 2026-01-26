from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

class RouteBlockerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/_next/") or path.startswith("/.git/"):
             return JSONResponse(status_code=404, content={"detail": "Static Asset Not Found"})
        return await call_next(request)
