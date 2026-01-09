from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    email_verified = Column(Boolean, default=False, nullable=False)

    preferred_language = Column(String, default="pt")

    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

