from sqlalchemy.orm import Session
from app.db.models.gamification import Badge, UserBadge
from app.db.models.user import User

BADGE_DEFINITIONS = [
    {"slug": "early-adopter", "name": "Pioneer", "desc": "One of the first users of the platform.", "icon": "🚀"},
    {"slug": "polymath", "name": "Polymath", "desc": "Possesses skills in 3 or more technologies.", "icon": "🧠"},
    {"slug": "interviewer", "name": "Communicator", "desc": "Completed a technical interview simulation.", "icon": "🎙️"},
    {"slug": "planner", "name": "Strategist", "desc": "Created their first study plan.", "icon": "🗺️"},
    {"slug": "guardian", "name": "Identity Guardian", "desc": "Connected GitHub and LinkedIn accounts for maximum security.", "icon": "🛡️"}
]

def init_badges(db: Session):
    """Ensures all badges exist in DB and are up-to-date."""
    # Fetch all existing badges
    existing_badges = {b.slug: b for b in db.query(Badge).all()}

    for b_def in BADGE_DEFINITIONS:
        if b_def["slug"] not in existing_badges:
            new_badge = Badge(
                slug=b_def["slug"],
                name=b_def["name"],
                description=b_def["desc"],
                icon=b_def["icon"]
            )
            db.add(new_badge)
        else:
             # Update existing if changed (Localization fix)
            badge = existing_badges[b_def["slug"]]
            if badge.name != b_def["name"] or badge.description != b_def["desc"]:
                badge.name = b_def["name"]
                badge.description = b_def["desc"]
                badge.icon = b_def["icon"]

    db.commit()

def award_badge(db: Session, user_id: int, badge_slug: str) -> bool:
    """Awards a badge to a user if they don't have it yet. Returns True if awarded."""
    badge = db.query(Badge).filter(Badge.slug == badge_slug).first()
    if not badge:
        return False

    # Check ownership
    has_badge = db.query(UserBadge).filter(
        UserBadge.user_id == user_id,
        UserBadge.badge_id == badge.id
    ).first()

    if has_badge:
        return False

    # Award
    new_user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(new_user_badge)
    db.commit()
    return True

def check_and_award_security_badge(db: Session, user: User) -> bool:
    """Checks if user has both GitHub and LinkedIn linked and awards the Guardian badge."""
    if user.github_id and user.linkedin_id:
        return award_badge(db, user.id, "guardian")
    return False
