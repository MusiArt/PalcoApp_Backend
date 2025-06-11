# tests/test_public_api.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session # Para configurar dados de teste, se necessário
from app import schemas, crud, models # Importe o que precisar
import datetime

# Fixtures test_app_client, db_session, test_musician virão de conftest.py

# --- Testes para Endpoints Públicos ---

def test_ler_lista_publica_de_musicos(
    test_app_client: TestClient, db_session: Session, test_musician: dict
):
    """
    Testa o endpoint público GET /musicos/ para listar músicos.
    A fixture test_musician já cria um músico. Vamos criar mais um para testar a lista.
    """
    # test_musician já foi criado pela fixture e estará ativo.
    # Criar um segundo músico ativo
    musico2_data = schemas.MusicoCreate(
        email="publicartist2@example.com",
        password="password123",
        nome_artistico="Artista Público Dois",
        is_active=True # Explicitamente, embora seja o padrão no modelo
    )
    crud.criar_musico(db=db_session, musico=musico2_data)

    # Criar um músico inativo (não deve aparecer na lista pública padrão)
    musico_inativo_data = schemas.MusicoCreate(
        email="inativo@example.com",
        password="password123",
        nome_artistico="Artista Inativo"
    )
    musico_inativo = crud.criar_musico(db=db_session, musico=musico_inativo_data)
    musico_inativo.is_active = False # Define como inativo
    db_session.add(musico_inativo)
    db_session.commit()

    response = test_app_client.get("/musicos/")
    assert response.status_code == 200
    lista_musicos = response.json()
    assert isinstance(lista_musicos, list)
    # Devemos ter pelo menos os dois músicos ativos que criamos/garantimos
    # A fixture test_musician cria 'Test Musician'
    assert len(lista_musicos) >= 2 
    
    nomes_artisticos = [m["nome_artistico"] for m in lista_musicos]
    assert test_musician["data_create"].nome_artistico in nomes_artisticos
    assert musico2_data.nome_artistico in nomes_artisticos
    assert musico_inativo_data.nome_artistico not in nomes_artisticos

    # Verifica se o schema é MusicoPublicProfile (não deve ter email)
    if lista_musicos:
        assert "email" not in lista_musicos[0] 
        assert "itens_repertorio" in lista_musicos[0] # Verifica se relacionamentos são incluídos
        assert "shows" in lista_musicos[0]


def test_ler_perfil_publico_de_musico_especifico(
    test_app_client: TestClient, test_musician: dict
):
    """Testa o endpoint público GET /musicos/{musico_id}/."""
    musico_id_existente = test_musician["obj_id"]

    response = test_app_client.get(f"/musicos/{musico_id_existente}")
    assert response.status_code == 200
    data_musico = response.json()
    assert data_musico["id"] == musico_id_existente
    assert data_musico["nome_artistico"] == test_musician["data_create"].nome_artistico
    assert "email" not in data_musico # Perfil público não deve ter email
    assert "itens_repertorio" in data_musico
    assert "shows" in data_musico


def test_ler_perfil_publico_de_musico_inexistente(test_app_client: TestClient):
    """Testa GET /musicos/{musico_id}/ para um músico que não existe."""
    response = test_app_client.get("/musicos/99999") # ID improvável de existir
    assert response.status_code == 404
    assert response.json()["detail"] == "Músico não encontrado ou inativo"


def test_ler_lista_publica_de_shows(
    test_app_client: TestClient, test_musician_token: str, test_musician: dict, db_session: Session
):
    """Testa o endpoint público GET /shows/ para listar todos os shows."""
    headers_musico = {"Authorization": f"Bearer {test_musician_token}"}
    musico_id = test_musician["obj_id"]

    # Adiciona alguns shows para músicos diferentes
    data_hora1 = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)).isoformat()
    show1_data = {"data_hora_evento": data_hora1, "local_nome": "Show Público 1", "musico_id": musico_id}
    test_app_client.post("/shows/", headers=headers_musico, json=show1_data) # Músico A cria show

    # Cria músico B e seu show
    musico_b_data = schemas.MusicoCreate(email="musico_show_publico@example.com", password="password123", nome_artistico="Músico B Shows Públicos")
    musico_b = crud.criar_musico(db=db_session, musico=musico_b_data)
    login_b_data = {"username": musico_b.email, "password": "password123"}
    token_b_res = test_app_client.post("/token", data=login_b_data)
    token_b = token_b_res.json()["access_token"]
    headers_musico_b = {"Authorization": f"Bearer {token_b}"}
    
    data_hora2 = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)).isoformat() # Show anterior ao show1
    show2_data = {"data_hora_evento": data_hora2, "local_nome": "Show Público 2 Antecipado", "musico_id": musico_b.id}
    test_app_client.post("/shows/", headers=headers_musico_b, json=show2_data) # Músico B cria show

    response = test_app_client.get("/shows/") # Endpoint público
    assert response.status_code == 200
    lista_shows = response.json()
    assert isinstance(lista_shows, list)
    assert len(lista_shows) >= 2

    # Verifica a ordem (deve ser por data_hora_evento ascendente)
    if len(lista_shows) >= 2:
        assert lista_shows[0]["local_nome"] == "Show Público 2 Antecipado" # O mais antigo primeiro
        assert lista_shows[1]["local_nome"] == "Show Público 1"
    
    # Verifica se os campos esperados estão presentes
    if lista_shows:
        assert "musico_id" in lista_shows[0] # O schema Show inclui musico_id


def test_ler_shows_de_musico_especifico_publico(
    test_app_client: TestClient, test_musician_token: str, test_musician: dict
):
    """Testa GET /musicos/{musico_id}/shows/."""
    headers_musico = {"Authorization": f"Bearer {test_musician_token}"}
    musico_id = test_musician["obj_id"]

    # Adiciona shows para este músico
    data_hora1 = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)).isoformat()
    test_app_client.post("/shows/", headers=headers_musico, json={"data_hora_evento": data_hora1, "local_nome": "Show do Musico Especifico 1"})
    
    data_hora2 = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat() # Mais antigo
    test_app_client.post("/shows/", headers=headers_musico, json={"data_hora_evento": data_hora2, "local_nome": "Show do Musico Especifico 0"})

    response = test_app_client.get(f"/musicos/{musico_id}/shows/")
    assert response.status_code == 200
    lista_shows_musico = response.json()
    assert isinstance(lista_shows_musico, list)
    assert len(lista_shows_musico) == 2
    assert lista_shows_musico[0]["local_nome"] == "Show do Musico Especifico 0" # Verifica ordem
    assert lista_shows_musico[1]["local_nome"] == "Show do Musico Especifico 1"
    for show in lista_shows_musico:
        assert show["musico_id"] == musico_id


def test_ler_shows_de_musico_especifico_inexistente(test_app_client: TestClient):
    """Testa GET /musicos/{musico_id}/shows/ para músico inexistente."""
    response = test_app_client.get("/musicos/99999/shows/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Músico não encontrado ou inativo"