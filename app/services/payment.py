import stripe
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuration
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    @staticmethod
    def create_customer(email: str, name: str) -> Optional[str]:
        """
        Creates a Stripe customer.
        Returns the Customer ID.
        """
        # Strictly enable mock only in dev AND if keys are missing
        if not stripe.api_key:
             if settings.ENVIRONMENT == "development":
                 logger.warning("Stripe Key missing. Using MOCK CUSTOMER in Development.")
                 return "cus_mock_12345"
             else:
                 logger.error("CRITICAL: Stripe Key missing in PRODUCTION. Payment failed.")
                 return None

        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            return customer.id
        except Exception as e:
            logger.error(f"Stripe Error (create_customer): {e}")
            if settings.ENVIRONMENT == "development":
                 return "cus_mock_fallback"
            return None

    @staticmethod
    def process_payment(
        amount_cents: int,
        currency: str,
        source_token: str,
        customer_id: str,
        description: str = "Payment"
    ) -> bool:
        """
        Process a one-time charge or setup for subscription.
        """
        if not stripe.api_key:
            if settings.ENVIRONMENT == "development":
                 logger.warning("Stripe Key missing. Using MOCK PAYMENT in Development.")
                 return True
            return False

        try:
            # Attach the source (card token) to the customer
            # (In modern Stripe, we use PaymentMethods, but for simplicity with tokens:)
            stripe.Customer.create_source(
                customer_id,
                source=source_token
            )

            stripe.Charge.create(
                amount=amount_cents,
                currency=currency,
                customer=customer_id,
                description=description
            )
            return True
        except Exception as e:
            logger.error(f"Stripe Error (process_payment): {e}")
            # Only mock in dev
            if settings.ENVIRONMENT == "development":
                if "Authentication failed" in str(e) or "Invalid API Key" in str(e):
                    logger.info("Mocking success due to invalid keys in sandbox.")
                    return True
            return False

    @staticmethod
    def create_subscription(customer_id: str, price_id: str) -> bool:
        """
        Creates a recurring subscription.
        """
        if not stripe.api_key:
             if settings.ENVIRONMENT == "development":
                 return True
             return False

        try:
            stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}]
            )
            return True
        except Exception as e:
            logger.error(f"Stripe Error (create_subscription): {e}")
            if "Authentication failed" in str(e):
                 return True
            return False
