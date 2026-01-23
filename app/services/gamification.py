from sqlalchemy.orm import Session
from app.db.models.gamification import Badge, UserBadge
from app.db.models.user import User

BADGE_DEFINITIONS = [
    {"slug": "early-adopter", "name": "Pioneiro", "desc": "Um dos primeiros usuários da plataforma.", "icon": "🚀"},
    {"slug": "polymath", "name": "Polímata", "desc": "Possui habilidades em 3 ou mais tecnologias.", "icon": "🧠"},
    {"slug": "interviewer", "name": "Comunicador", "desc": "Completou uma simulação de entrevista técnica.", "icon": "🎙️"},
    {"slug": "planner", "name": "Estrategista", "desc": "Criou seu primeiro plano de estudos.", "icon": "🗺️"},
    {"slug": "guardian", "name": "Guardião da Identidade", "desc": "Conectou contas do GitHub e LinkedIn para máxima segurança.", "icon": "🛡️"}
]

def init_badges(db: Session):
    """Ensures all badges exist in DB."""
    # Fetch all existing badge slugs in a single query to avoid N+1.
    existing_slugs = {slug for slug, in db.query(Badge.slug).all()}

    for b_def in BADGE_DEFINITIONS:
        if b_def["slug"] not in existing_slugs:
            new_badge = Badge(
                slug=b_def["slug"],
                name=b_def["name"],
                description=b_def["desc"],
                icon=b_def["icon"]
            )
            db.add(new_badge)
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
