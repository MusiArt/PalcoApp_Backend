# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.pool import StaticPool

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.main import app
from app.database import Base, get_db
# Importe todos os modelos que serão criados/usados
from app.models import Musico, UsuarioPublico # Adicionado UsuarioPublico
# Importe esquemas usados nas fixtures
from app.schemas import MusicoCreate, UsuarioPublicoCreate # Adicionado UsuarioPublicoCreate

SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

@pytest.fixture(scope="function")
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)

@pytest.fixture(scope="function")
def db_session(setup_database) -> SQLAlchemySession:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function") # Mudado para function para alinhar com db_session e setup_database
def test_app_client(setup_database): 
    def override_get_db_test():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db_test
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

# --- Fixtures de Dados de Teste ---
@pytest.fixture(scope="function")
def test_musician(db_session: SQLAlchemySession):
    from app.crud import criar_musico

    musician_data_create = MusicoCreate(
        email="testmusician@example.com",
        password="testpassword123",
        nome_artistico="Test Musician"
    )
    musician_obj_db = criar_musico(db=db_session, musico=musician_data_create)
    # Retornar dados que não dependem da sessão que será fechada aqui
    return {"data_create": musician_data_create, "obj_id": musician_obj_db.id, "email": musician_obj_db.email}

@pytest.fixture(scope="function")
def test_musician_token(test_app_client: TestClient, test_musician: dict):
    login_data = {
        "username": test_musician["data_create"].email,
        "password": test_musician["data_create"].password,
    }
    response = test_app_client.post("/token", data=login_data) # Endpoint de login de músico
    assert response.status_code == 200, f"Login de músico falhou no teste: {response.json()}"
    return response.json()["access_token"]

# --- NOVAS FIXTURES PARA FÃS ABAIXO ---
@pytest.fixture(scope="function")
def test_fan(db_session: SQLAlchemySession): # Usa a sessão de teste limpa
    from app.crud import criar_usuario_publico # Importa a função de criar fã

    fan_data_create = UsuarioPublicoCreate( # Usa o schema de criação de fã
        email="testfan@example.com",
        password="testfanpassword123",
        nome_completo="Test Fan One"
    )
    fan_obj_db = criar_usuario_publico(db=db_session, usuario=fan_data_create)
    # Retorna dados úteis para outros testes
    return {"data_create": fan_data_create, "id": fan_obj_db.id, "email": fan_obj_db.email}

@pytest.fixture(scope="function")
def test_fan_token(test_app_client: TestClient, test_fan: dict): # Usa o cliente de teste e a fixture test_fan
    login_data = {
        "username": test_fan["data_create"].email,
        "password": test_fan["data_create"].password,
    }
    # Usa o endpoint de login de fã
    response = test_app_client.post("/usuarios/token", data=login_data) 
    assert response.status_code == 200, f"Login de fã falhou no teste: {response.json()}"
    return response.json()["access_token"]