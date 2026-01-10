from fastapi import HTTPException, status, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime
from app.db.models.user import User

def check_subscription_status(user: User):
    """
    Checks if the user's trial has expired and they haven't paid.
    Returns True if access is allowed.
    Returns False if access should be denied.
    """

    # 1. Check if user is active subscriber
    if user.subscription_status == 'active':
        # Check if expired (if we track end date strictly)
        if user.subscription_end_date and user.subscription_end_date > datetime.utcnow():
            return True
        elif user.is_recurring:
             return True

    # 2. Check Trial
    days_since_creation = (datetime.utcnow() - user.created_at).days
    if days_since_creation < 30:
        return True

    # 3. If we are here, Trial is over AND not active.
    return False
