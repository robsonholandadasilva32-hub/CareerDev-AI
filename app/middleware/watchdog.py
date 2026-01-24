import time
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.core.utils import get_client_ip
from app.db.session import SessionLocal
from app.services.security_service import log_audit

logger = logging.getLogger(__name__)

class WatchdogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Store failure timestamps per IP
        # Structure: {ip_address: [timestamp1, timestamp2, ...]}
        self.ip_tracker = defaultdict(list)
        self.THRESHOLD = 10
        self.WINDOW = 300  # 5 minutes in seconds

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only monitor strictly HTTP 401 responses
        if response.status_code == 401:
            ip = get_client_ip(request)
            now = time.time()

            # Add current failure
            self.ip_tracker[ip].append(now)

            # Cleanup old failures and check count
            # Filter keep only failures within WINDOW
            self.ip_tracker[ip] = [t for t in self.ip_tracker[ip] if now - t <= self.WINDOW]

            if not self.ip_tracker[ip]:
                del self.ip_tracker[ip]
            elif len(self.ip_tracker[ip]) > self.THRESHOLD:
                msg = f"Potential Intrusion Detected: IP {ip} exceeded {self.THRESHOLD} failed attempts in {self.WINDOW}s."
                logger.warning(msg)

                # Write to Audit Log
                db = SessionLocal()
                try:
                    log_audit(
                        db=db,
                        user_id=None,
                        action="WARNING",
                        ip_address=ip,
                        details={"message": msg, "count": len(self.ip_tracker[ip])}
                    )
                except Exception as e:
                    logger.error(f"Failed to log watchdog event to DB: {e}")
                finally:
                    db.close()

        return response
