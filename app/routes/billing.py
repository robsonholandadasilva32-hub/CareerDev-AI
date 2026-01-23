from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
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
@router.get("/subscription/checkout")
def upgrade_page(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    user = db.query(User).filter(User.id == user_id).first()

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    # Mock Flow for Dev/Test (if no Stripe Key)
    if not stripe.api_key:
        logger.warning("Stripe API Key missing. Using Mock Mode.")
        return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "client_secret": "mock_secret",
            "publishable_key": "pk_test_mock",
            "user": user
        })

    try:
        # 1. Create Customer if missing
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            db.commit()

        # 2. Create Subscription
        # We use ad-hoc price_data for simplicity in this pivot.
        # In a real app, you'd likely use a fixed Price ID from config.
        subscription = stripe.Subscription.create(
            customer=user.stripe_customer_id,
            items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'CareerDev AI Premium',
                        'description': 'Unlimited AI Access & Career Insights'
                    },
                    'unit_amount': 999, # $9.99
                    'recurring': {
                        'interval': 'month',
                    },
                },
            }],
            payment_behavior='default_incomplete',
            payment_settings={'save_default_payment_method': 'on_subscription'},
            expand=['latest_invoice.payment_intent'],
        )

        # 3. Extract Client Secret
        client_secret = subscription.latest_invoice.payment_intent.client_secret

        log_audit(db, user_id, "CHECKOUT_INIT", request.client.host, f"Sub ID: {subscription.id}")

        return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "client_secret": client_secret,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "user": user
        })

    except Exception as e:
        logger.error(f"Stripe Error: {e}")
        print(f"STRIPE ERROR: {e}")
        log_audit(db, user_id, "CHECKOUT_ERROR", request.client.host, f"Stripe Exception: {e}")
        return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "error": "Payment system unavailable. Please try again later.",
            "user": user,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "client_secret": None
        })


@router.get("/billing/success")
def billing_success(
    request: Request,
    payment_intent: str = None,
    payment_intent_client_secret: str = None,
    redirect_status: str = None,
    db: Session = Depends(get_db)
):
    """
    Stripe redirects here after Elements payment.
    We verify the PaymentIntent status.
    """
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    # Mock Bypass
    if not stripe.api_key:
         user = db.query(User).filter(User.id == user_id).first()
         user.is_premium = True
         user.subscription_status = "active"
         db.commit()
         return RedirectResponse("/dashboard?success=premium_activated")

    try:
        if not payment_intent:
             return RedirectResponse("/dashboard?error=missing_payment_intent")

        intent = stripe.PaymentIntent.retrieve(payment_intent)

        if intent.status == 'succeeded':
            user = db.query(User).filter(User.id == user_id).first()
            user.is_premium = True
            user.subscription_status = "active"
            db.commit()

            log_audit(db, user_id, "SUBSCRIPTION_ACTIVE", request.client.host, f"Stripe Intent: {payment_intent}")
            return RedirectResponse("/dashboard?success=premium_activated")
        elif intent.status == 'processing':
            log_audit(db, user_id, "SUBSCRIPTION_PROCESSING", request.client.host, f"Stripe Intent: {payment_intent}")
            return RedirectResponse("/dashboard?info=payment_processing")
        else:
            log_audit(db, user_id, "SUBSCRIPTION_FAIL", request.client.host, f"Status: {intent.status}")
            return RedirectResponse("/dashboard?error=payment_failed")

    except Exception as e:
        logger.error(f"Stripe Verification Error: {e}")
        log_audit(db, user_id, "SUBSCRIPTION_VERIFY_FAIL", request.client.host, f"Stripe Exception: {e}")
        return RedirectResponse("/dashboard?error=verification_failed")
