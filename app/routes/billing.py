from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import stripe
import logging
from app.db.session import get_db
from app.core.config import settings
from app.core.auth_guard import get_current_user_from_request
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import log_audit
from app.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.get("/subscription/upgrade")
def upgrade_page(request: Request):
    return templates.TemplateResponse("subscription/upgrade_premium.html", {"request": request, "t": {}, "lang": "pt"})

@router.get("/billing/checkout")
def create_checkout_session(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    user = db.query(User).filter(User.id == user_id).first()

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    log_audit(db, user_id, "CHECKOUT_START", request.client.host, "Initiated Premium Checkout")

    if not stripe.api_key:
        # Mock Flow for Demo/Dev
        user.is_premium = True
        user.subscription_status = "active"
        db.commit()
        log_audit(db, user_id, "SUBSCRIPTION_ACTIVE", request.client.host, "Mocked Payment Success")
        return RedirectResponse("/dashboard?success=premium_mocked")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'brl',
                        'product_data': {
                            'name': 'CareerDev AI Premium',
                        },
                        'unit_amount': 2990, # R$ 29,90
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=str(request.base_url) + 'billing/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=str(request.base_url) + 'subscription/upgrade',
            customer_email=user.email,
        )
        return RedirectResponse(checkout_session.url, status_code=303)
    except Exception as e:
        logger.error(f"Stripe Error: {e}")
        log_audit(db, user_id, "CHECKOUT_ERROR", request.client.host, f"Stripe Exception: {e}")
        return RedirectResponse("/dashboard?error=payment_failed")

@router.get("/billing/success")
def billing_success(session_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    # If keys are missing (Mock/Dev), allow bypass
    if not stripe.api_key:
         user = db.query(User).filter(User.id == user_id).first()
         user.is_premium = True
         user.subscription_status = "active"
         db.commit()
         return RedirectResponse("/dashboard?success=premium_activated")

    # Secure Verification
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            user = db.query(User).filter(User.id == user_id).first()
            user.is_premium = True
            user.subscription_status = "active"
            user.stripe_customer_id = session.customer
            db.commit()

            log_audit(db, user_id, "SUBSCRIPTION_ACTIVE", request.client.host, f"Stripe Verified ID: {session_id}")

            return RedirectResponse("/dashboard?success=premium_activated")
        else:
            log_audit(db, user_id, "SUBSCRIPTION_PENDING", request.client.host, f"Stripe ID: {session_id} Pending")
            return RedirectResponse("/dashboard?error=payment_pending")
    except Exception as e:
        logger.error(f"Stripe Verification Error: {e}")
        log_audit(db, user_id, "SUBSCRIPTION_VERIFY_FAIL", request.client.host, f"Stripe Exception: {e}")
        return RedirectResponse("/dashboard?error=verification_failed")
