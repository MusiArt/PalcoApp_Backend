# tests/test_shows.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas, crud, models # Importe tudo o que precisar
import datetime # Para lidar com datas e horas

# As fixtures test_app_client, db_session, test_musician, test_musician_token, test_fan_token
# virão de conftest.py

# --- Testes para Endpoints de Shows ---

def test_adicionar_show_sucesso(test_app_client: TestClient, test_musician_token: str):
    """Testa adicionar um novo show com sucesso."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    # Certifique-se de que a data e hora estão no formato ISO correto e são para o futuro
    # para evitar problemas com possíveis lógicas de validação de data no futuro.
    data_hora_futura = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()
    
    dados_show = {
        "data_hora_evento": data_hora_futura,
        "local_nome": "Arena Teste Shows",
        "local_endereco": "Rua dos Testes, 100",
        "descricao_evento": "Um grande show de teste!",
        "link_evento": "https://eventos.example.com/show-teste"
    }
    
    response = test_app_client.post("/shows/", headers=headers, json=dados_show)
    
    assert response.status_code == 201, f"Erro ao adicionar show: {response.json()}"
    data_resposta = response.json()
    assert data_resposta["local_nome"] == dados_show["local_nome"]
    assert data_resposta["link_evento"] == dados_show["link_evento"]
    assert "id" in data_resposta
    assert "musico_id" in data_resposta # O músico logado deve ser o dono


def test_ler_shows_do_musico_logado(test_app_client: TestClient, test_musician_token: str):
    """Testa listar os shows do músico logado."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    
    # Adiciona alguns shows primeiro
    show1_data = {
        "data_hora_evento": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10)).isoformat(),
        "local_nome": "Show A Arena", "link_evento": "https://link.com/a"
    }
    res_create1 = test_app_client.post("/shows/", headers=headers, json=show1_data)
    assert res_create1.status_code == 201
    
    show2_data = {
        "data_hora_evento": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=12)).isoformat(),
        "local_nome": "Show B Palco", "link_evento": "https://link.com/b"
    }
    res_create2 = test_app_client.post("/shows/", headers=headers, json=show2_data)
    assert res_create2.status_code == 201
    
    response = test_app_client.get("/shows/me/", headers=headers) # Endpoint para shows do músico logado
    assert response.status_code == 200, f"Erro ao ler shows do músico: {response.json()}"
    
    data_resposta = response.json()
    assert isinstance(data_resposta, list)
    assert len(data_resposta) >= 2 
    
    nomes_locais_shows = [show["local_nome"] for show in data_resposta]
    assert show1_data["local_nome"] in nomes_locais_shows
    assert show2_data["local_nome"] in nomes_locais_shows


def test_atualizar_show_sucesso(test_app_client: TestClient, test_musician_token: str):
    """Testa atualizar um show com sucesso."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    
    data_hora_original = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=15)).isoformat()
    dados_originais = {
        "data_hora_evento": data_hora_original,
        "local_nome": "Local Original Show",
        "link_evento": "https://original.com"
    }
    response_create = test_app_client.post("/shows/", headers=headers, json=dados_originais)
    assert response_create.status_code == 201
    show_id = response_create.json()["id"]
    
    data_hora_atualizada = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=20)).isoformat()
    dados_atualizacao = {
        "local_nome": "Local ATUALIZADO Show!",
        "descricao_evento": "Descrição adicionada na atualização.",
        "data_hora_evento": data_hora_atualizada,
        "link_evento": "https://atualizado.com/"
    }
    response_update = test_app_client.put(f"/shows/{show_id}", headers=headers, json=dados_atualizacao)
    
    assert response_update.status_code == 200, f"Erro ao atualizar show: {response_update.json()}"
    data_atualizada = response_update.json()
    assert data_atualizada["local_nome"] == dados_atualizacao["local_nome"]
    assert data_atualizada["descricao_evento"] == dados_atualizacao["descricao_evento"]
    assert data_atualizada["link_evento"] == dados_atualizacao["link_evento"]
    # Para comparar datetimes, pode ser necessário parseá-los de volta se o formato da string variar ligeiramente.
    # Mas se o FastAPI/Pydantic os serializa consistentemente, a comparação de strings pode funcionar.
    # É mais seguro comparar objetos datetime se possível, ou verificar se o valor mudou significativamente.
    assert data_atualizada["id"] == show_id


def test_deletar_show_sucesso(test_app_client: TestClient, test_musician_token: str):
    """Testa deletar um show com sucesso."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    
    data_hora_show_deletar = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=25)).isoformat()
    dados_show = {
        "data_hora_evento": data_hora_show_deletar,
        "local_nome": "Show a Ser Deletado",
        "link_evento": "https://delete.me"
    }
    response_create = test_app_client.post("/shows/", headers=headers, json=dados_show)
    assert response_create.status_code == 201
    show_id = response_create.json()["id"]
    
    response_delete = test_app_client.delete(f"/shows/{show_id}", headers=headers)
    assert response_delete.status_code == 204
    
    # Verifica se o show foi removido
    response_get_all = test_app_client.get("/shows/me/", headers=headers) # Verifica os shows do músico
    shows_musico = response_get_all.json()
    show_encontrado = next((s for s in shows_musico if s["id"] == show_id), None)
    assert show_encontrado is None


def test_tentar_acessar_shows_sem_token(test_app_client: TestClient):
    """Testa acessar endpoints protegidos de shows sem token."""
    data_hora_teste = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    response_post = test_app_client.post("/shows/", json={"data_hora_evento": data_hora_teste, "local_nome": "Teste"})
    assert response_post.status_code == 401
    
    response_get = test_app_client.get("/shows/me/")
    assert response_get.status_code == 401

    response_put = test_app_client.put("/shows/999", json={"local_nome": "Teste"})
    assert response_put.status_code == 401

    response_delete = test_app_client.delete("/shows/999")
    assert response_delete.status_code == 401

def test_musico_nao_pode_alterar_show_de_outro_musico(
    test_app_client: TestClient,
    test_musician_token: str, # Token do Músico A
    db_session: Session
):
    headers_musico_a = {"Authorization": f"Bearer {test_musician_token}"}
    
    data_hora_show_a = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=35)).isoformat()
    show_data_musico_a = {"data_hora_evento": data_hora_show_a, "local_nome": "Show do Músico A"}
    response_create_a = test_app_client.post("/shows/", headers=headers_musico_a, json=show_data_musico_a)
    assert response_create_a.status_code == 201
    show_id_musico_a = response_create_a.json()["id"]

    musician_b_schema_create = schemas.MusicoCreate(
        email="musicob_show@example.com", password="passwordb_show", nome_artistico="Músico B Shows"
    )
    musico_b_db = crud.criar_musico(db=db_session, musico=musician_b_schema_create)
    
    login_data_b = {"username": musico_b_db.email, "password": "passwordb_show"}
    response_login_b = test_app_client.post("/token", data=login_data_b)
    assert response_login_b.status_code == 200
    token_musico_b = response_login_b.json()["access_token"]
    headers_musico_b = {"Authorization": f"Bearer {token_musico_b}"}

    response_put_b_on_a = test_app_client.put(
        f"/shows/{show_id_musico_a}", 
        headers=headers_musico_b, 
        json={"local_nome": "Tentativa de Hack Show"}
    )
    assert response_put_b_on_a.status_code == 404
    assert response_put_b_on_a.json()["detail"] == "Show não encontrado ou não pertence ao músico"

    response_delete_b_on_a = test_app_client.delete(f"/shows/{show_id_musico_a}", headers=headers_musico_b)
    assert response_delete_b_on_a.status_code == 404
    assert response_delete_b_on_a.json()["detail"] == "Show não encontrado ou não pertence ao músico"

def test_fan_nao_pode_gerenciar_shows(test_app_client: TestClient, test_fan_token: str):
    """Testa se um fã não pode gerenciar shows."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    data_hora_teste_fan = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=40)).isoformat()
    
    response_post = test_app_client.post("/shows/", headers=headers_fan, json={"data_hora_evento": data_hora_teste_fan, "local_nome": "Show do Fan"})
    assert response_post.status_code == 403
    assert response_post.json()["detail"] == "Acesso não permitido para este tipo de usuário"

    response_get = test_app_client.get("/shows/me/", headers=headers_fan) # Endpoint para shows do músico logado
    assert response_get.status_code == 403
    assert response_get.json()["detail"] == "Acesso não permitido para este tipo de usuário"