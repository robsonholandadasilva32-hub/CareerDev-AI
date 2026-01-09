from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from app.db.models.email_verification import EmailVerification
from app.db.models.user import User


def create_email_verification(db: Session, user_id: int):
    code = str(random.randint(100000, 999999))

    verification = EmailVerification(
        user_id=user_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )

    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


def get_verification_by_user(db: Session, user_id: int):
    return db.query(EmailVerification).filter(
        EmailVerification.user_id == user_id
    ).first()


def verify_code(db: Session, user_id: int, code: str) -> bool:
    verification = get_verification_by_user(db, user_id)

    if not verification:
        return False

    if verification.code != code:
        return False

    if verification.expires_at < datetime.utcnow():
        return False

    user = db.query(User).get(user_id)
    user.email_verified = True

    db.delete(verification)
    db.commit()
    return True

