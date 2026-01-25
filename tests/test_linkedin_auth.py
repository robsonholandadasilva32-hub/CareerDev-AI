import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import os

# --- Configuração de Ambiente de Teste ---
# Define variáveis ANTES de importar a app para evitar erros de validação no config.py
os.environ["LINKEDIN_CLIENT_ID"] = "test_client_id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "test_client_secret"
os.environ["GITHUB_CLIENT_ID"] = "test_github_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_github_secret"
os.environ["SESSION_SECRET_KEY"] = "super-secret-key"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db

# --- Configuração do Banco de Dados para Teste ---
# Usa um arquivo SQLite específico para evitar problemas de thread/concorrência nos testes async
DB_FILE = "./test_linkedin.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"

# check_same_thread=False é crucial para testes assíncronos com SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_engine():
    """Cria o banco de dados antes dos testes e o apaga depois (Teardown)."""
    Base.metadata.create_all(bind=engine)
    yield engine
    # Limpeza
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

@pytest.fixture(scope="function")
def db(db_engine):
    """
    Cria uma nova sessão de banco de dados para cada teste.
    Aplica patches cruciais para evitar erros de 'Session is closed' no middleware.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Patch para o get_db da aplicação usar nossa sessão de teste
    app.dependency_overrides[get_db] = lambda: session

    # TRUQUE TÉCNICO (CRÍTICO): Impede que o AuthMiddleware feche a sessão prematuramente.
    # Salvamos o método original e o substituímos por um 'dummy' temporário.
    original_close = session.close
    session.close = lambda: None

    # Garante que o middleware de auth também use essa sessão
    with patch("app.middleware.auth.SessionLocal", lambda: session):
        yield session

    # Restaura o close original e limpa tudo após o teste
    session.close = original_close
    session.close()
    transaction.rollback()
    connection.close()
    
    # Limpa override
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="function")
def client(db):
    """Retorna um TestClient configurado."""
    with TestClient(app) as c:
        yield c

# --- TESTES ---

@pytest.mark.asyncio
async def test_linkedin_callback_missing_nonce_handled(client, db):
    """
    Testa se o callback do LinkedIn relaxa a exigência do 'nonce'
    e transita com sucesso para a etapa de conexão com o GitHub (Novo Usuário).
    """

    # Mock dos dados retornados pelo LinkedIn (SEM o campo nonce no id_token)
    mock_token = {
        "access_token": "fake_token",
        "token_type": "bearer",
        "expires_in": 3600,
        "id_token": "fake_id_token_without_nonce"
    }

    mock_user_info = {
        "sub": "linkedin_12345",
        "email": "testuser@example.com",
        "given_name": "Test",
        "family_name": "User",
        "picture": "http://example.com/avatar.jpg"
    }

    # Mockamos o cliente OAuth do LinkedIn dentro da rota
    with patch("app.routes.social.oauth.linkedin.authorize_access_token", new_callable=AsyncMock) as mock_auth_token, \
         patch("app.routes.social.oauth.linkedin.userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_auth_token.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # AÇÃO: Chamar a rota de callback
        response = client.get("/auth/linkedin/callback", follow_redirects=False)

        # VALIDAÇÃO 1: Verificamos se 'authorize_access_token' foi chamado com a configuração correta
        # Isso confirma que o Hotfix está ativo (claims_options={'nonce': {'required': False}})
        args, kwargs = mock_auth_token.call_args
        assert "claims_options" in kwargs
        assert kwargs["claims_options"]["nonce"]["required"] is False

        # VALIDAÇÃO 2: Integridade do Fluxo (Zero-Touch)
        # Como o usuário é novo (não tem GitHub), deve redirecionar para conectar GitHub
        assert response.status_code == 303
        assert response.headers["location"] == "/onboarding/connect-github"

        # Verifica se o usuário foi criado no banco
        user = db.query(User).filter_by(email="testuser@example.com").first()
        assert user is not None
        assert user.linkedin_id == "linkedin_12345"
        assert user.github_id is None
        assert user.terms_accepted is True # Aceite implícito

@pytest.mark.asyncio
async def test_linkedin_callback_zero_touch_flow(client, db):
    """
    Testa se um usuário que JÁ tem GitHub é enviado direto para o Dashboard.
    Isso garante a integridade da cadeia de login.
    """

    # Pré-cria usuário com LinkedIn E GitHub
    user = User(
        email="existing@example.com",
        name="Existing User",
        linkedin_id="linkedin_999",
        github_id="github_888",
        hashed_password="hashed_secret",
        terms_accepted=True
    )
    db.add(user)
    db.commit()

    mock_token = {"access_token": "fake", "id_token": "fake_id"}
    mock_user_info = {
        "sub": "linkedin_999",
        "email": "existing@example.com",
        "name": "Existing User"
    }

    with patch("app.routes.social.oauth.linkedin.authorize_access_token", new_callable=AsyncMock) as mock_auth_token, \
         patch("app.routes.social.oauth.linkedin.userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_auth_token.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # Ação
        response = client.get("/auth/linkedin/callback", follow_redirects=False)

        # Validação: Deve ir para DASHBOARD (Zero Touch)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        # Confirma novamente que o nonce estava desligado
        _, kwargs = mock_auth_token.call_args
        assert kwargs["claims_options"]["nonce"]["required"] is False

@pytest.mark.asyncio
async def test_linkedin_callback_security_state_validation(client, db):
    """
    Testa se a validação de estado (CSRF) ainda ocorre implicitamente.
    Simulamos o Authlib lançando um erro de estado para garantir que não quebra o app.
    """

    with patch("app.routes.social.oauth.linkedin.authorize_access_token", new_callable=AsyncMock) as mock_auth_token:
        # Simula erro de validação (MismatchingStateError)
        mock_auth_token.side_effect = Exception("MismatchingStateError")

        response = client.get("/auth/linkedin/callback", follow_redirects=False)

        # Deve redirecionar para login com mensagem de erro
        assert response.status_code == 307 or response.status_code == 303
        assert "/login?error=linkedin_failed" in response.headers["location"]