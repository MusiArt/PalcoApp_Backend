# tests/test_pedidos.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas, crud, models
import datetime

# Fixtures: test_app_client, db_session,
# test_musician, test_musician_token,
# test_fan, test_fan_token
# virão de conftest.py

# Helper para criar um item de repertório para um músico nos testes
def criar_item_repertorio_teste(client: TestClient, token_musico: str, nome_musica: str, artista: str) -> dict:
    headers = {"Authorization": f"Bearer {token_musico}"}
    response = client.post("/repertorio/", headers=headers, json={"nome_musica": nome_musica, "artista_original": artista})
    assert response.status_code == 201
    return response.json()

# --- Testes para Endpoints de Pedidos de Música ---

def test_fan_cria_pedido_de_musica_sucesso(
    test_app_client: TestClient, test_fan_token: str, test_musician: dict, test_musician_token: str
):
    """Testa um fã logado criando um pedido de música com sucesso."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id_alvo = test_musician["obj_id"]

    # Músico (dono do token test_musician_token) adiciona um item ao seu repertório
    item_repertorio_criado = criar_item_repertorio_teste(
        test_app_client, test_musician_token, "Música Pedida Teste", "Artista do Teste"
    )
    item_repertorio_id_alvo = item_repertorio_criado["id"]

    dados_pedido = {
        "musico_id": musico_id_alvo,
        "item_repertorio_id": item_repertorio_id_alvo,
        "mensagem_opcional": "Por favor, toque esta!"
    }
    
    response = test_app_client.post("/pedidos/", headers=headers_fan, json=dados_pedido)
    
    assert response.status_code == 201, f"Erro ao criar pedido: {response.json()}"
    data_resposta = response.json()
    assert data_resposta["item_repertorio_pedido"]["id"] == item_repertorio_id_alvo
    assert data_resposta["musico_destinatario"]["id"] == musico_id_alvo
    assert data_resposta["status_pedido"] == "pendente"
    assert data_resposta["mensagem_opcional"] == dados_pedido["mensagem_opcional"]
    assert "id" in data_resposta # ID do pedido


def test_listar_pedidos_feitos_pelo_fan(
    test_app_client: TestClient, test_fan_token: str, test_fan: dict, test_musician: dict, test_musician_token: str
):
    """Testa o fã logado listando os pedidos que ele fez."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id_alvo = test_musician["obj_id"]
    item1 = criar_item_repertorio_teste(test_app_client, test_musician_token, "Musica Pedido Fan 1", "A1")
    item2 = criar_item_repertorio_teste(test_app_client, test_musician_token, "Musica Pedido Fan 2", "A2")

    # Fan faz dois pedidos
    test_app_client.post("/pedidos/", headers=headers_fan, json={"musico_id": musico_id_alvo, "item_repertorio_id": item1["id"]})
    test_app_client.post("/pedidos/", headers=headers_fan, json={"musico_id": musico_id_alvo, "item_repertorio_id": item2["id"]})
    
    response = test_app_client.get("/usuarios/me/pedidos/", headers=headers_fan)
    assert response.status_code == 200
    lista_pedidos = response.json()
    assert isinstance(lista_pedidos, list)
    assert len(lista_pedidos) == 2
    assert lista_pedidos[0]["item_repertorio_pedido"]["id"] == item2["id"] # Mais recente primeiro (devido ao order_by no CRUD)
    assert lista_pedidos[1]["item_repertorio_pedido"]["id"] == item1["id"]


def test_listar_pedidos_recebidos_pelo_musico(
    test_app_client: TestClient, test_fan_token: str, test_fan: dict, test_musician: dict, test_musician_token: str
):
    """Testa o músico logado listando os pedidos que ele recebeu."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    headers_musico = {"Authorization": f"Bearer {test_musician_token}"}
    musico_id_alvo = test_musician["obj_id"]
    fan_id_solicitante = test_fan["id"]
    
    item1 = criar_item_repertorio_teste(test_app_client, test_musician_token, "Musica para Musico A", "Artista M")
    
    # Fan faz um pedido para o Músico A
    res_pedido = test_app_client.post(
        "/pedidos/", 
        headers=headers_fan, 
        json={"musico_id": musico_id_alvo, "item_repertorio_id": item1["id"]}
    )
    assert res_pedido.status_code == 201
    
    response = test_app_client.get("/musicos/me/pedidos/", headers=headers_musico) # Logado como Músico A
    assert response.status_code == 200
    lista_pedidos_musico = response.json()
    assert isinstance(lista_pedidos_musico, list)
    assert len(lista_pedidos_musico) == 1
    assert lista_pedidos_musico[0]["item_repertorio_pedido"]["id"] == item1["id"]
    assert lista_pedidos_musico[0]["solicitante"]["id"] == fan_id_solicitante


def test_musico_atualiza_status_pedido_sucesso(
    test_app_client: TestClient, test_fan_token: str, test_musician: dict, test_musician_token: str
):
    """Testa o músico logado atualizando o status de um pedido."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    headers_musico = {"Authorization": f"Bearer {test_musician_token}"}
    musico_id_alvo = test_musician["obj_id"]
    item_repertorio = criar_item_repertorio_teste(test_app_client, test_musician_token, "Musica Status", "Artista Status")

    # Fan faz o pedido
    response_pedido = test_app_client.post(
        "/pedidos/", 
        headers=headers_fan, 
        json={"musico_id": musico_id_alvo, "item_repertorio_id": item_repertorio["id"]}
    )
    assert response_pedido.status_code == 201
    pedido_id = response_pedido.json()["id"]
    
    # Músico atualiza o status
    novo_status = {"status_pedido": "atendido"}
    response_update = test_app_client.patch(f"/pedidos/{pedido_id}/status", headers=headers_musico, json=novo_status)
    
    assert response_update.status_code == 200, f"Erro ao atualizar status: {response_update.json()}"
    data_atualizada = response_update.json()
    assert data_atualizada["status_pedido"] == "atendido"
    assert data_atualizada["id"] == pedido_id

    # Verifica se o status realmente mudou (opcional, buscando o pedido)
    response_get_pedido_musico = test_app_client.get("/musicos/me/pedidos/", headers=headers_musico)
    pedidos_musico = response_get_pedido_musico.json()
    pedido_encontrado = next((p for p in pedidos_musico if p["id"] == pedido_id), None)
    assert pedido_encontrado is not None
    assert pedido_encontrado["status_pedido"] == "atendido"


def test_fan_nao_pode_atualizar_status_pedido(
    test_app_client: TestClient, test_fan_token: str, test_musician: dict, test_musician_token: str
):
    """Testa se um fã não pode atualizar o status de um pedido."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"} # Token do Fã
    headers_musico = {"Authorization": f"Bearer {test_musician_token}"}
    musico_id_alvo = test_musician["obj_id"]
    item_repertorio = criar_item_repertorio_teste(test_app_client, test_musician_token, "Musica Fan Update", "Artista Fan Update")

    # Fan faz o pedido
    response_pedido = test_app_client.post(
        "/pedidos/", 
        headers=headers_fan, 
        json={"musico_id": musico_id_alvo, "item_repertorio_id": item_repertorio["id"]}
    )
    assert response_pedido.status_code == 201
    pedido_id = response_pedido.json()["id"]

    # Fã tenta atualizar o status
    novo_status_fan = {"status_pedido": "hackeado"}
    response_update_fan = test_app_client.patch(f"/pedidos/{pedido_id}/status", headers=headers_fan, json=novo_status_fan)
    
    assert response_update_fan.status_code == 403 # Forbidden, pois o endpoint espera um músico
    assert response_update_fan.json()["detail"] == "Acesso não permitido para este tipo de usuário"


def test_pedir_musica_item_repertorio_invalido(
    test_app_client: TestClient, test_fan_token: str, test_musician: dict
):
    """Testa pedir uma música com item_repertorio_id que não existe ou não pertence ao músico."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id_alvo = test_musician["obj_id"]
    item_repertorio_id_invalido = 99999

    dados_pedido = {
        "musico_id": musico_id_alvo,
        "item_repertorio_id": item_repertorio_id_invalido,
    }
    response = test_app_client.post("/pedidos/", headers=headers_fan, json=dados_pedido)
    assert response.status_code == 404
    assert response.json()["detail"] == "Item de repertório não encontrado ou não pertence ao músico especificado"