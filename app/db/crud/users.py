from sqlalchemy.orm import Session
from app.db.models.user import User

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def get_user_by_github_id(db: Session, github_id: str) -> User | None:
    return db.query(User).filter(User.github_id == github_id).first()

def get_user_by_linkedin_id(db: Session, linkedin_id: str) -> User | None:
    return db.query(User).filter(User.linkedin_id == linkedin_id).first()

def create_user(
    db: Session,
    name: str,
    email: str,
    hashed_password: str,
    **kwargs
) -> User:
    user = User(
        name=name,
        email=email,
        hashed_password=hashed_password,
        **kwargs
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
