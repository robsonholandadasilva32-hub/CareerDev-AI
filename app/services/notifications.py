import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models.otp import OTP

def generate_otp_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def create_otp(db: Session, user_id: int, method: str):
    code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    otp = OTP(
        user_id=user_id,
        code=code,
        method=method,
        expires_at=expires_at
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    # Mock sending (Log to console)
    print(f"========================================")
    print(f"[MOCK NOTIFICATION] To User {user_id} via {method}")
    print(f"Code: {code}")
    print(f"========================================")

    return otp

def verify_otp(db: Session, user_id: int, code: str):
    otp = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.code == code,
        OTP.expires_at > datetime.utcnow()
    ).first()

    if otp:
        # Delete OTP after use to prevent replay
        db.delete(otp)
        db.commit()
        return True
    return False
