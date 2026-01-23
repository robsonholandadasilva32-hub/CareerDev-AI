import pytest
from playwright.sync_api import Page, expect
import time
import random
import re
import uuid
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.security import UserSession
from app.core.jwt import create_access_token

# Função auxiliar para criar usuário verificado no DB
def setup_verified_user(db):
    timestamp = int(time.time())
    rand = random.randint(1000, 9999)
    email = f"test_{timestamp}_{rand}@example.com"

    user = User(
        name="Test User",
        email=email,
        hashed_password="mock_hash_bypass", 
        email_verified=True,
        is_profile_completed=True, # Crítico para evitar redirect loop
        terms_accepted=True,
        subscription_status='free',
        linkedin_id=f"li_{timestamp}_{rand}",
        github_id=f"gh_{timestamp}_{rand}",
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_user_flow(page: Page):
    """
    Testa o fluxo completo: Login via Cookie -> Dashboard (English) -> Checkout (Stripe Elements)
    """
    db = SessionLocal()
    
    try:
        # 1. Setup User
        user = setup_verified_user(db)

        # 2. Create Session (Manual - Obrigatório para gerar o token com SID correto)
        session = UserSession(
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Playwright Test Runner",
            last_active_at=datetime.utcnow(),
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 3. Generate Valid JWT (Incluindo 'sid')
        token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "sid": str(session.id)
        })

        # 4. Inject Cookie (Configuração robusta para Localhost)
        page.context.add_cookies([{
            "name": "access_token",
            "value": token,
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
            "secure": False, # False para rodar localmente sem HTTPS
            "sameSite": "Lax"
        }])

        # 5. Navegar para Dashboard (Smoke Test)
        page.goto("http://localhost:8000/dashboard")
        
        # Assert: Não deve redirecionar para login
        expect(page).not_to_have_url(re.compile(".*login.*"))
        
        # Assert: Verifica texto em INGLÊS (Freemium Policy)
        # "Some features are available for free" deve estar visível
        expect(page.locator("body")).to_contain_text("Some features are available for free")

        # 6. Navegar para a Página Unificada de Pagamento
        page.goto("http://localhost:8000/subscription/checkout")

        # Assert: Verifica se o container do Stripe Elements carregou
        # Isso confirma que a PaymentIntent/Subscription foi criada no backend
        expect(page.locator("#payment-element")).to_be_visible()

    finally:
        db.close()