# tests/test_repertorio.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session # Para interagir com o banco diretamente, se necessário
from app import schemas # Para usar os esquemas Pydantic nos dados de teste
from app import crud # <<<--- IMPORTAÇÃO ADICIONADA AQUI
from app import models # Para verificar tipos de objetos do banco, se necessário

# As fixtures test_app_client, db_session, test_musician_token, test_fan_token
# virão de conftest.py

# --- Testes para Endpoints de Repertório ---

def test_adicionar_item_repertorio_sucesso(test_app_client: TestClient, test_musician_token: str):
    """Testa adicionar um item ao repertório com sucesso."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    dados_item = {"nome_musica": "Nova Canção Teste", "artista_original": "Artista Famoso Teste"}
    
    response = test_app_client.post("/repertorio/", headers=headers, json=dados_item)
    
    assert response.status_code == 201, f"Erro ao adicionar item: {response.json()}"
    data_resposta = response.json()
    assert data_resposta["nome_musica"] == dados_item["nome_musica"]
    assert data_resposta["artista_original"] == dados_item["artista_original"]
    assert "id" in data_resposta


def test_ler_repertorio_do_musico_logado(test_app_client: TestClient, test_musician_token: str):
    """Testa listar o repertório do músico logado."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    
    # Adiciona alguns itens primeiro para garantir que há algo para listar
    item1_data = {"nome_musica": "Música Teste A", "artista_original": "Artista Teste X"}
    res_create1 = test_app_client.post("/repertorio/", headers=headers, json=item1_data)
    assert res_create1.status_code == 201
    
    item2_data = {"nome_musica": "Música Teste B", "artista_original": "Artista Teste Y"}
    res_create2 = test_app_client.post("/repertorio/", headers=headers, json=item2_data)
    assert res_create2.status_code == 201
    
    response = test_app_client.get("/repertorio/", headers=headers)
    assert response.status_code == 200, f"Erro ao ler repertório: {response.json()}"
    
    data_resposta = response.json()
    assert isinstance(data_resposta, list)
    # Verificamos se pelo menos os dois itens que adicionamos estão lá.
    # O banco é limpo por teste, então não deve haver mais do que isso, a menos que este teste adicione mais.
    assert len(data_resposta) == 2 # Assumindo que este teste só adiciona esses dois.
    
    nomes_musicas_resposta = [item["nome_musica"] for item in data_resposta]
    assert item1_data["nome_musica"] in nomes_musicas_resposta
    assert item2_data["nome_musica"] in nomes_musicas_resposta


def test_atualizar_item_repertorio_sucesso(test_app_client: TestClient, test_musician_token: str):
    """Testa atualizar um item de repertório com sucesso."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    
    dados_originais = {"nome_musica": "Música Original para Atualizar", "artista_original": "Artista Antigo Atualizar"}
    response_create = test_app_client.post("/repertorio/", headers=headers, json=dados_originais)
    assert response_create.status_code == 201
    item_id = response_create.json()["id"]
    
    dados_atualizacao = {"nome_musica": "Música Super Atualizada!", "artista_original": "Artista Novo e Melhor"}
    response_update = test_app_client.put(f"/repertorio/{item_id}", headers=headers, json=dados_atualizacao)
    
    assert response_update.status_code == 200, f"Erro ao atualizar item: {response_update.json()}"
    data_atualizada = response_update.json()
    assert data_atualizada["nome_musica"] == dados_atualizacao["nome_musica"]
    assert data_atualizada["artista_original"] == dados_atualizacao["artista_original"]
    assert data_atualizada["id"] == item_id


def test_deletar_item_repertorio_sucesso(test_app_client: TestClient, test_musician_token: str):
    """Testa deletar um item de repertório com sucesso."""
    headers = {"Authorization": f"Bearer {test_musician_token}"}
    
    dados_item = {"nome_musica": "Música Efêmera", "artista_original": "Artista Sumiço"}
    response_create = test_app_client.post("/repertorio/", headers=headers, json=dados_item)
    assert response_create.status_code == 201
    item_id = response_create.json()["id"]
    
    response_delete = test_app_client.delete(f"/repertorio/{item_id}", headers=headers)
    assert response_delete.status_code == 204
    
    response_get_all = test_app_client.get("/repertorio/", headers=headers)
    itens_repertorio = response_get_all.json()
    item_encontrado = next((item for item in itens_repertorio if item["id"] == item_id), None)
    assert item_encontrado is None


def test_tentar_acessar_repertorio_sem_token(test_app_client: TestClient):
    """Testa acessar endpoints de repertório sem token."""
    response_post = test_app_client.post("/repertorio/", json={"nome_musica": "Teste Sem Token"})
    assert response_post.status_code == 401
    
    response_get = test_app_client.get("/repertorio/")
    assert response_get.status_code == 401

    # Para PUT e DELETE, precisamos de um item_id. Como não podemos criar sem token,
    # testamos com um ID arbitrário, esperando 401 antes de qualquer outra verificação.
    response_put = test_app_client.put("/repertorio/999", json={"nome_musica": "Teste Sem Token"})
    assert response_put.status_code == 401

    response_delete = test_app_client.delete("/repertorio/999")
    assert response_delete.status_code == 401


def test_musico_nao_pode_alterar_repertorio_de_outro_musico(
    test_app_client: TestClient,
    test_musician_token: str, # Token do Músico A
    db_session: Session # Sessão do banco para criar o Músico B
):
    headers_musico_a = {"Authorization": f"Bearer {test_musician_token}"}
    
    # Músico A adiciona um item ao seu repertório
    item_data_musico_a = {"nome_musica": "Música Secreta do A", "artista_original": "Músico A"}
    response_create_a = test_app_client.post("/repertorio/", headers=headers_musico_a, json=item_data_musico_a)
    assert response_create_a.status_code == 201
    item_id_musico_a = response_create_a.json()["id"]

    # Cria um segundo músico (Músico B) diretamente no banco de teste
    musician_b_schema_create = schemas.MusicoCreate( # Usa o schema importado
        email="musicob_invasor@example.com", 
        password="passwordB123", 
        nome_artistico="Músico B Invasor"
    )
    # Usa crud.criar_musico (que agora está importado)
    musico_b_db = crud.criar_musico(db=db_session, musico=musician_b_schema_create)
    
    # Faz login como Músico B para obter seu token
    login_data_b = {"username": musico_b_db.email, "password": "passwordB123"}
    response_login_b = test_app_client.post("/token", data=login_data_b) # /token é para músicos
    assert response_login_b.status_code == 200
    token_musico_b = response_login_b.json()["access_token"]
    headers_musico_b = {"Authorization": f"Bearer {token_musico_b}"}

    # Músico B (logado) tenta ATUALIZAR o item do Músico A
    response_put_b_on_a = test_app_client.put(
        f"/repertorio/{item_id_musico_a}", 
        headers=headers_musico_b, 
        json={"nome_musica": "Música Hackeada"}
    )
    assert response_put_b_on_a.status_code == 404 
    assert response_put_b_on_a.json()["detail"] == "Item de repertório não encontrado ou não pertence ao músico"

    # Músico B (logado) tenta DELETAR o item do Músico A
    response_delete_b_on_a = test_app_client.delete(f"/repertorio/{item_id_musico_a}", headers=headers_musico_b)
    assert response_delete_b_on_a.status_code == 404
    assert response_delete_b_on_a.json()["detail"] == "Item de repertório não encontrado ou não pertence ao músico"


def test_fan_nao_pode_gerenciar_repertorio(test_app_client: TestClient, test_fan_token: str): # Usa a fixture test_fan_token
    """Testa se um fã (com token de fã) não pode gerenciar repertório."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"} # Token de Fã
    
    # Fã tenta adicionar item ao repertório (de quem?)
    response_post_fan = test_app_client.post("/repertorio/", headers=headers_fan, json={"nome_musica": "Fan Tentando Adicionar"})
    assert response_post_fan.status_code == 403 
    assert response_post_fan.json()["detail"] == "Acesso não permitido para este tipo de usuário"

    # Fã tenta listar o "seu" repertório (fãs não têm repertório diretamente)
    response_get_fan = test_app_client.get("/repertorio/", headers=headers_fan)
    assert response_get_fan.status_code == 403
    assert response_get_fan.json()["detail"] == "Acesso não permitido para este tipo de usuário"