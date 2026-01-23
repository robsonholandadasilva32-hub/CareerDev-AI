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
from app.core.utils import get_client_ip

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

    # 0. Check if already premium locally
    if user.is_premium and user.subscription_status == 'active':
        return RedirectResponse("/dashboard?info=already_premium")

    try:
        ip = get_client_ip(request)

        # 1. Create Customer if missing
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            db.commit()

        # 2. Check for existing subscriptions (Active or Incomplete)
        existing_subs = stripe.Subscription.list(
            customer=user.stripe_customer_id,
            limit=5
        )

        active_sub = next((s for s in existing_subs.data if s.status == 'active'), None)
        incomplete_sub = next((s for s in existing_subs.data if s.status in ['incomplete', 'past_due']), None)

        if active_sub:
            # Sync local state
            if not user.is_premium:
                user.is_premium = True
                user.subscription_status = 'active'
                db.commit()
            return RedirectResponse("/dashboard?success=restored_premium")

        client_secret = None

        if incomplete_sub:
            # Reuse existing incomplete subscription
            logger.info(f"Reusing incomplete subscription {incomplete_sub.id} for user {user.id}")

            # Retrieve latest invoice to get payment intent
            invoice = stripe.Invoice.retrieve(incomplete_sub.latest_invoice)
            if invoice.payment_intent:
                pi = stripe.PaymentIntent.retrieve(invoice.payment_intent)
                client_secret = pi.client_secret
            else:
                 # Should not happen for incomplete subs created via Elements, but safer to just create new if failed
                 logger.warning(f"Incomplete sub {incomplete_sub.id} has no payment intent. Creating new.")
                 client_secret = None

        if not client_secret:
            # Create NEW Subscription
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
            client_secret = subscription.latest_invoice.payment_intent.client_secret
            log_audit(db, user_id, "CHECKOUT_INIT", ip, f"Sub ID: {subscription.id}")

        return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "client_secret": client_secret,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "user": user
        })

    except stripe.error.AuthenticationError:
        logger.error("Stripe Authentication Error: Invalid API Keys")
        return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "error": "Erro de Configuração: Chaves do Stripe não encontradas ou inválidas.",
            "user": user,
            "publishable_key": None,
            "client_secret": None
        })
    except stripe.error.StripeError as e:
         logger.error(f"Stripe API Error: {e}")
         return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "error": "Erro no processamento do pagamento. Tente novamente.",
            "user": user,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "client_secret": None,
            "debug_error": str(e) if settings.ENVIRONMENT != 'production' else None
        })
    except Exception as e:
        logger.exception(f"Checkout Error: {e}")
        log_audit(db, user_id, "CHECKOUT_ERROR", get_client_ip(request), f"Exception: {e}")
        return templates.TemplateResponse("subscription/checkout.html", {
            "request": request,
            "error": "Sistema de pagamento temporariamente indisponível.",
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

    ip = get_client_ip(request)

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

            log_audit(db, user_id, "SUBSCRIPTION_ACTIVE", ip, f"Stripe Intent: {payment_intent}")
            return RedirectResponse("/dashboard?success=premium_activated")
        elif intent.status == 'processing':
            log_audit(db, user_id, "SUBSCRIPTION_PROCESSING", ip, f"Stripe Intent: {payment_intent}")
            return RedirectResponse("/dashboard?info=payment_processing")
        else:
            log_audit(db, user_id, "SUBSCRIPTION_FAIL", ip, f"Status: {intent.status}")
            return RedirectResponse("/dashboard?error=payment_failed")

    except Exception as e:
        logger.error(f"Stripe Verification Error: {e}")
        log_audit(db, user_id, "SUBSCRIPTION_VERIFY_FAIL", ip, f"Stripe Exception: {e}")
        return RedirectResponse("/dashboard?error=verification_failed")
