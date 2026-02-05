
from fastapi import Request, Depends
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.gamification import UserBadge

def get_user_with_profile(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Retrieves the current authenticated user and eagerly loads
    their CareerProfile and Badges to prevent DetachedInstanceError.

    This replaces direct usage of `request.state.user` in routes
    that need to access these relationships.
    """
    # 1. Check if AuthMiddleware found a user
    if not getattr(request.state, "user", None):
        return None

    user_id = request.state.user.id

    # 2. Reload User with Eager Loading (JoinedLoad)
    # We load both career_profile (for Career routes) and badges (for Dashboard)
    # to satisfy the requirement of a single consolidated dependency.
    user = (
        db.query(User)
        .options(
            joinedload(User.career_profile),
            joinedload(User.badges).joinedload(UserBadge.badge)
        )
        .filter(User.id == user_id)
        .first()
    )
    return user
