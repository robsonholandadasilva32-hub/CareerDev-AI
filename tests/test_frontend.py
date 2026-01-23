import pytest
from playwright.sync_api import Page, expect
import time
import random
import re
import uuid
from datetime import datetime, timezone
from app.db.session import SessionLocal
from app.db.models.user import User

# Imports abaixo são necessários para o registro do SQLAlchemy resolver os relacionamentos de User
from app.db.models.security import UserSession, AuditLog
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
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
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Nova função para usuário incompleto (Onboarding)
def setup_incomplete_user(db):
    timestamp = int(time.time())
    rand = random.randint(1000, 9999)
    email = f"new_{timestamp}_{rand}@example.com"

    user = User(
        name="", # Nome vazio para simular início
        email=email,
        hashed_password="mock_hash_bypass",
        email_verified=True, # Padrão do sistema agora (bypass)
        is_profile_completed=False, # Força fluxo de onboarding
        terms_accepted=False,
        subscription_status='free',
        linkedin_id=f"li_{timestamp}_{rand}",
        github_id=f"gh_{timestamp}_{rand}",
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_billing_access_redirect(page: Page):
    """
    Verifies that accessing the billing page without login redirects to login.
    """
    # Access billing directly
    page.goto("http://localhost:8000/payment/checkout")

    # Should redirect to login
    expect(page).to_have_url(re.compile(".*login"))

def test_user_flow(page: Page):
    """
    Testa o fluxo completo: Login via Cookie -> Dashboard (English) -> Checkout (Stripe Hosted)
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
            last_active_at=datetime.now(timezone.utc),
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
        
        # Assert: Não deve redirecionar para verificação de e-mail (Bypass Logic)
        expect(page).not_to_have_url(re.compile(".*verify-email.*"))

        # Assert: Não deve redirecionar para login
        expect(page).not_to_have_url(re.compile(".*login.*"))
        
        # Assert: Verifica texto em INGLÊS (Freemium Policy)
        # "Some features are available for free" deve estar visível
        expect(page.locator("body")).to_contain_text("Some features are available for free")

        # 6. Navegar para a Página de Checkout
        page.goto("http://localhost:8000/payment/checkout")

        # Assert: Como não temos chaves do Stripe, ele deve redirecionar para o dashboard com erro
        # Ou se tiver chaves (em CI), vai para o Stripe.
        # Vamos assumir que sem chaves ele redireciona para dashboard com erro.
        expect(page).to_have_url(re.compile(".*dashboard.*error.*"))

    finally:
        db.close()

def test_onboarding_bypass(page: Page):
    """
    Testa o fluxo de Onboarding REMOVIDO:
    Login (Incompleto) -> Redirect Dashboard (IMEDIATO)
    """
    db = SessionLocal()

    try:
        # 1. Setup Incomplete User
        user = setup_incomplete_user(db)

        # 2. Create Session
        session = UserSession(
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Playwright Test Runner",
            last_active_at=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 3. Generate Token
        token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "sid": str(session.id)
        })

        # 4. Inject Cookie
        page.context.add_cookies([{
            "name": "access_token",
            "value": token,
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax"
        }])

        # 5. Tentar acessar Dashboard
        page.goto("http://localhost:8000/dashboard")

        # Assert: Não deve redirecionar para verificação de e-mail (Bypass Logic)
        expect(page).not_to_have_url(re.compile(".*verify-email.*"))

        # Assert: DEVE redirecionar diretamente para o Dashboard, pulando onboarding
        expect(page).to_have_url(re.compile(".*dashboard"))
        expect(page).not_to_have_url(re.compile(".*onboarding.*"))

        # Verify content to ensure full access
        expect(page.locator("body")).to_contain_text("Some features are available for free")

    finally:
        db.close()
