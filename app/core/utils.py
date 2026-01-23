from fastapi import Request

def get_client_ip(request: Request) -> str:
    """
    Extracts the client's real IP address, trusting X-Forwarded-For if present.
    Essential for applications running behind proxies (Railway, Heroku, Nginx).
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # The first IP in the list is the client's original IP
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "0.0.0.0"
