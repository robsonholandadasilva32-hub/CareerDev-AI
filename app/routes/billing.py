from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.db.models.user import User
import os
from app.services.payment import PaymentService
from app.i18n.loader import i18n

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/billing", response_class=HTMLResponse)
async def view_billing(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Load translations
    t = i18n.get_text(current_user.preferred_language)

    stripe_pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_placeholder")

    return templates.TemplateResponse("billing.html", {
        "request": request,
        "user": current_user,
        "t": t,
        "stripe_pk": stripe_pk
    })

@router.post("/billing/pay")
async def process_payment(
    request: Request,
    stripeToken: str = Form(...),
    recurring: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    t = i18n.get_text(current_user.preferred_language)

    # 1. Create Customer if needed
    if not current_user.stripe_customer_id:
        customer_id = PaymentService.create_customer(current_user.email, current_user.name)
        current_user.stripe_customer_id = customer_id
        db.commit()
    else:
        customer_id = current_user.stripe_customer_id

    # 2. Process Payment
    # Price is $1.00 = 100 cents
    amount = 100

    success = False
    if recurring:
        # Create Subscription
        # We assume a price ID exists for the $1 plan. In real world, we configure this in Stripe Dashboard.
        # For this exercise, we mock it or pass a dummy ID.
        success = PaymentService.create_subscription(customer_id, "price_12345_monthly")
    else:
        # One time charge
        success = PaymentService.process_payment(amount, "usd", stripeToken, customer_id, "Monthly Access")

    if success:
        current_user.subscription_status = 'active'
        current_user.is_recurring = recurring
        # If not recurring, we give 30 days. If recurring, we assume auto-renew.
        current_user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
        db.commit()

        return RedirectResponse(url="/dashboard?payment_success=true", status_code=status.HTTP_302_FOUND)
    else:
        stripe_pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_placeholder")
        return templates.TemplateResponse("billing.html", {
            "request": request,
            "user": current_user,
            "t": t,
            "error": "Payment failed. Please try again.",
            "stripe_pk": stripe_pk
        })
