from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import stripe
import logging
from app.core.config import settings
from app.db.session import get_db
from app.db.models.user import User
from app.core.auth_guard import get_current_user_from_request
from app.services.security_service import log_audit
from app.core.utils import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.get("/payment/checkout")
def create_checkout_session(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse("/login")

    # If already premium, redirect to dashboard
    if user.is_premium and user.subscription_status == 'active':
        return RedirectResponse("/dashboard?info=already_premium")

    try:
        # Create Customer if missing
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            db.commit()

        # Create Session
        checkout_session = stripe.checkout.Session.create(
            client_reference_id=str(user.id),
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    # Provide the exact Price ID (for example, stored in env vars)
                    # or creating one on the fly (less ideal for prod but works for dev)
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'CareerDev AI Premium',
                        },
                        'unit_amount': 999,
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=settings.DOMAIN + '/dashboard?success=premium_activated',
            cancel_url=settings.DOMAIN + '/dashboard?info=payment_cancelled',
        )
        return RedirectResponse(checkout_session.url, status_code=303)

    except Exception as e:
        logger.error(f"Stripe Checkout Error: {e}")
        return RedirectResponse("/dashboard?error=payment_system_error")


@router.post("/payment/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = stripe_signature
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Webhook Error: Invalid payload - {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Webhook Error: Invalid signature - {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session, db)

    return {"status": "success"}

def handle_checkout_session_completed(session, db: Session):
    client_reference_id = session.get('client_reference_id')
    stripe_customer_id = session.get('customer')

    logger.info(f"Payment Success for User ID: {client_reference_id}")

    if client_reference_id:
        user = db.query(User).filter(User.id == int(client_reference_id)).first()
        if user:
            user.is_premium = True
            user.subscription_status = 'active'
            user.stripe_customer_id = stripe_customer_id
            db.commit()
            log_audit(db, user.id, "SUBSCRIPTION_ACTIVE", "WEBHOOK", f"Session: {session.get('id')}")
        else:
            logger.error(f"User not found for ID: {client_reference_id}")
