from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import stripe
from app.db.session import get_db
from app.core.config import settings
from app.core.auth_guard import get_current_user_from_request
from app.db.models.user import User

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.get("/billing/checkout")
def create_checkout_session(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    user = db.query(User).filter(User.id == user_id).first()

    if not stripe.api_key:
        # Mock Flow for Demo
        user.is_premium = True
        db.commit()
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
            cancel_url=str(request.base_url) + 'dashboard',
            customer_email=user.email,
        )
        return RedirectResponse(checkout_session.url, status_code=303)
    except Exception as e:
        print(f"Stripe Error: {e}")
        return RedirectResponse("/dashboard?error=payment_failed")

@router.get("/billing/success")
def billing_success(session_id: str, request: Request, db: Session = Depends(get_db)):
    # In prod, verify session_id with Stripe
    # For now, trust and upgrade
    user_id = get_current_user_from_request(request)
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        user.is_premium = True
        db.commit()

    return RedirectResponse("/dashboard?success=premium_activated")
