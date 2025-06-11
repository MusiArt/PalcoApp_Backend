# tests/test_musicians.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas, crud, models # Garanta que models está importado se precisar verificar tipos

# As fixtures test_app_client, db_session, test_musician, test_musician_token virão de conftest.py

# --- Testes de Cadastro (Existentes) ---
def test_criar_novo_musico_sucesso(test_app_client: TestClient, db_session: Session):
    dados_musico = {
        "nome_artistico": "Artista Teste Um",
        "email": "artistateste1@example.com",
        "password": "senhaSuperSegura123",
        "generos_musicais": "Rock Experimental",
        "descricao": "Um artista de teste para cadastro.",
        "link_gorjeta": "https://pix.example.com/artistateste1"
    }
    response = test_app_client.post("/musicos/", json=dados_musico)
    assert response.status_code == 201
    data_resposta = response.json()
    assert data_resposta["email"] == dados_musico["email"]
    assert data_resposta["nome_artistico"] == dados_musico["nome_artistico"]
    assert "id" in data_resposta
    assert "hashed_password" not in data_resposta
    assert data_resposta["is_active"] == True
    assert data_resposta["itens_repertorio"] == []
    assert data_resposta["shows"] == []
    musico_db = crud.obter_musico_por_email(db_session, email=dados_musico["email"])
    assert musico_db is not None
    assert musico_db.nome_artistico == dados_musico["nome_artistico"]

def test_criar_musico_email_duplicado(test_app_client: TestClient, test_musician: dict, db_session: Session):
    dados_musico_duplicado = {
        "nome_artistico": "Outro Artista",
        "email": test_musician["data_create"].email, # Usa o mesmo email da fixture
        "password": "outrasenha456"
    }
    response = test_app_client.post("/musicos/", json=dados_musico_duplicado)
    assert response.status_code == 400
    assert response.json() == {"detail": "Email já registrado"}

def test_criar_musico_senha_curta(test_app_client: TestClient):
    dados_musico_senha_curta = {
        "nome_artistico": "Artista Senha Curta",
        "email": "senhacurta@example.com",
        "password": "123" 
    }
    response = test_app_client.post("/musicos/", json=dados_musico_senha_curta)
    assert response.status_code == 422
    data_resposta = response.json()
    assert "detail" in data_resposta
    assert any("password" in error["loc"] for error in data_resposta["detail"])

def test_criar_musico_email_invalido(test_app_client: TestClient):
    dados_musico_email_invalido = {
        "nome_artistico": "Artista Email Ruim",
        "email": "naoeumemailvalido",
        "password": "senhavalida123"
    }
    response = test_app_client.post("/musicos/", json=dados_musico_email_invalido)
    assert response.status_code == 422
    data_resposta = response.json()
    assert "detail" in data_resposta
    assert any("email" in error["loc"] for error in data_resposta["detail"])

# --- NOVOS TESTES DE LOGIN E PERFIL DO MÚSICO ABAIXO ---

def test_login_musico_sucesso(test_app_client: TestClient, test_musician: dict):
    """
    Testa o login de um músico com credenciais corretas.
    A fixture test_musician já criou o músico no banco.
    """
    login_data = {
        "username": test_musician["data_create"].email,
        "password": test_musician["data_create"].password # Usa a senha original em texto plano
    }
    response = test_app_client.post("/token", data=login_data) # data= para form data
    
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    # Poderíamos tentar decodificar o token aqui para verificar 'sub' e 'role',
    # mas isso exigiria importar SECRET_KEY e ALGORITHM, o que pode ser feito.


def test_login_musico_senha_incorreta(test_app_client: TestClient, test_musician: dict):
    """Testa o login de um músico com senha incorreta."""
    login_data = {
        "username": test_musician["data_create"].email,
        "password": "senhaincorreta"
    }
    response = test_app_client.post("/token", data=login_data)
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Email ou senha incorretos"}

def test_login_musico_email_nao_existe(test_app_client: TestClient):
    """Testa o login com um email que não está cadastrado."""
    login_data = {
        "username": "naoexiste@example.com",
        "password": "qualquersenha"
    }
    response = test_app_client.post("/token", data=login_data)
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Email ou senha incorretos"} # A mensagem é a mesma para email ou senha errada

def test_ler_perfil_musico_logado_sucesso(test_app_client: TestClient, test_musician_token: str, test_musician: dict):
    """
    Testa o acesso ao endpoint /musicos/me/ com um token válido.
    A fixture test_musician_token já faz o login e retorna o token.
    """
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    response = test_app_client.get("/musicos/me/", headers=headers)
    
    assert response.status_code == 200
    data_resposta = response.json()
    assert data_resposta["email"] == test_musician["data_create"].email
    assert data_resposta["nome_artistico"] == test_musician["data_create"].nome_artistico
    assert data_resposta["id"] == test_musician["obj_id"] # Verifica o ID do músico criado
    assert "itens_repertorio" in data_resposta # Verifica se a chave do repertório está presente
    assert "shows" in data_resposta # Verifica se a chave de shows está presente


def test_ler_perfil_musico_logado_sem_token(test_app_client: TestClient):
    """Testa o acesso ao endpoint /musicos/me/ sem um token."""
    response = test_app_client.get("/musicos/me/") # Sem cabeçalho Authorization
    
    assert response.status_code == 401 # Espera Não Autorizado
    # A resposta detalhada pode variar dependendo se o FastAPI retorna
    # "Not authenticated" ou a mensagem da sua exceção em decodificar_validar_token.
    # Geralmente é "Not authenticated" se nenhum token é fornecido.
    assert response.json()["detail"] == "Not authenticated"


def test_ler_perfil_musico_logado_token_invalido(test_app_client: TestClient):
    """Testa o acesso ao endpoint /musicos/me/ com um token inválido/malformado."""
    headers = {"Authorization": "Bearer tokenmuitoinvalido"}
    response = test_app_client.get("/musicos/me/", headers=headers)
    
    assert response.status_code == 401
    # A mensagem de detalhe aqui virá da exceção em decodificar_validar_token
    assert response.json()["detail"] == "Não foi possível validar as credenciais"