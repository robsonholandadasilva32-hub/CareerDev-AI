from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

