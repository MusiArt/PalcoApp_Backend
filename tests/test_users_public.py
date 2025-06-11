# tests/test_users_public.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas, crud, models

# As fixtures test_app_client, db_session virão de conftest.py
# Vamos criar fixtures específicas para usuários do público em conftest.py também

def test_criar_novo_usuario_publico_sucesso(test_app_client: TestClient, db_session: Session):
    """
    Testa o cadastro de um novo usuário do público (fã) com sucesso.
    """
    dados_usuario = {
        "email": "fan1@example.com",
        "password": "fanpassword123",
        "nome_completo": "Super Fan Um"
    }
    
    response = test_app_client.post("/usuarios/", json=dados_usuario)
    
    assert response.status_code == 201, f"Erro: {response.json()}" # Adiciona detalhe do erro se falhar
    
    data_resposta = response.json()
    assert data_resposta["email"] == dados_usuario["email"]
    assert data_resposta["nome_completo"] == dados_usuario["nome_completo"]
    assert "id" in data_resposta
    assert "hashed_password" not in data_resposta # Garante que a senha hasheada não é retornada
    assert data_resposta["is_active"] == True # Verifica o valor padrão
    assert "data_cadastro" in data_resposta
    assert data_resposta["musicos_favoritos"] == [] # Deve começar sem favoritos

    # Verifica diretamente no banco de dados
    usuario_db = crud.obter_usuario_publico_por_email(db_session, email=dados_usuario["email"])
    assert usuario_db is not None
    assert usuario_db.nome_completo == dados_usuario["nome_completo"]


def test_criar_usuario_publico_email_duplicado(test_app_client: TestClient, test_fan: dict): # Usa a futura fixture test_fan
    """
    Testa a tentativa de cadastrar um fã com um email que já existe.
    """
    dados_usuario_duplicado = {
        "email": test_fan["data_create"].email, # Usa o mesmo email da fixture test_fan
        "password": "outrasenhafan",
        "nome_completo": "Outro Fan"
    }
    
    response = test_app_client.post("/usuarios/", json=dados_usuario_duplicado)
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Email já registrado para um usuário"}


def test_criar_usuario_publico_senha_curta(test_app_client: TestClient):
    """
    Testa a tentativa de cadastrar um fã com uma senha muito curta.
    """
    dados_usuario_senha_curta = {
        "email": "fansenhacurta@example.com",
        "password": "fan", # Senha curta
        "nome_completo": "Fan Senha Curta"
    }
    
    response = test_app_client.post("/usuarios/", json=dados_usuario_senha_curta)
    
    assert response.status_code == 422
    data_resposta = response.json()
    assert "detail" in data_resposta
    assert any("password" in error["loc"] for error in data_resposta["detail"])


def test_login_fan_sucesso(test_app_client: TestClient, test_fan: dict):
    """
    Testa o login de um fã com credenciais corretas.
    """
    login_data = {
        "username": test_fan["data_create"].email,
        "password": test_fan["data_create"].password
    }
    response = test_app_client.post("/usuarios/token", data=login_data)
    
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_login_fan_senha_incorreta(test_app_client: TestClient, test_fan: dict):
    """Testa o login de um fã com senha incorreta."""
    login_data = {
        "username": test_fan["data_create"].email,
        "password": "senhaincorretafan"
    }
    response = test_app_client.post("/usuarios/token", data=login_data)
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Email ou senha incorretos"}


def test_ler_perfil_fan_logado_sucesso(test_app_client: TestClient, test_fan_token: str, test_fan: dict):
    """
    Testa o acesso ao endpoint /usuarios/me/ com um token de fã válido.
    """
    headers = {"Authorization": f"Bearer {test_fan_token}"}
    response = test_app_client.get("/usuarios/me/", headers=headers)
    
    assert response.status_code == 200
    data_resposta = response.json()
    assert data_resposta["email"] == test_fan["data_create"].email
    assert data_resposta["nome_completo"] == test_fan["data_create"].nome_completo
    assert data_resposta["id"] == test_fan["id"] # Usa o id do objeto do banco
    assert "musicos_favoritos" in data_resposta # Verifica se a chave de favoritos está presente


def test_ler_perfil_fan_logado_sem_token(test_app_client: TestClient):
    """Testa o acesso ao endpoint /usuarios/me/ sem um token."""
    response = test_app_client.get("/usuarios/me/")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_ler_perfil_fan_logado_token_invalido(test_app_client: TestClient):
    """Testa o acesso ao endpoint /usuarios/me/ com um token inválido."""
    headers = {"Authorization": "Bearer tokenfaninvalido"}
    response = test_app_client.get("/usuarios/me/", headers=headers)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Não foi possível validar as credenciais"

def test_ler_perfil_fan_logado_com_token_de_musico(test_app_client: TestClient, test_musician_token: str):
    """
    Testa o acesso ao endpoint /usuarios/me/ (que é para fãs)
    usando um token de músico. Deve falhar.
    """
    headers = {"Authorization": f"Bearer {test_musician_token}"} # Usa token de músico
    response = test_app_client.get("/usuarios/me/", headers=headers)
    
    assert response.status_code == 403 # Forbidden
    assert response.json()["detail"] == "Acesso não permitido para este tipo de usuário"