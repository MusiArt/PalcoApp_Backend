# tests/test_favorites.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas, crud, models

# Fixtures virão de conftest.py

def test_fan_favorita_musico_sucesso(
    test_app_client: TestClient, 
    test_fan_token: str, 
    test_musician: dict, 
    db_session: Session,
    test_fan: dict
):
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id_a_favoritar = test_musician["obj_id"]

    response_favoritar = test_app_client.post(f"/musicos/{musico_id_a_favoritar}/favoritar", headers=headers_fan)
    assert response_favoritar.status_code == 200, f"Erro ao favoritar: {response_favoritar.json()}"
    
    data_resposta_favoritar = response_favoritar.json()
    assert any(musico["id"] == musico_id_a_favoritar for musico in data_resposta_favoritar.get("musicos_favoritos", [])), \
        f"Músico ID {musico_id_a_favoritar} não encontrado em musicos_favoritos: {data_resposta_favoritar.get('musicos_favoritos')}"

    fan_id = test_fan["id"]
    db_fan = crud.obter_usuario_publico_por_id(db_session, usuario_id=fan_id)
    assert db_fan is not None
    assert any(musico.id == musico_id_a_favoritar for musico in db_fan.musicos_favoritos), \
        f"Músico ID {musico_id_a_favoritar} não encontrado nos favoritos do fã no DB."


def test_fan_tenta_favoritar_musico_duas_vezes(
    test_app_client: TestClient, test_fan_token: str, test_musician: dict
):
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id = test_musician["obj_id"]

    response1 = test_app_client.post(f"/musicos/{musico_id}/favoritar", headers=headers_fan)
    assert response1.status_code == 200

    response2 = test_app_client.post(f"/musicos/{musico_id}/favoritar", headers=headers_fan)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Músico já está nos seus favoritos"


def test_fan_desfavorita_musico_sucesso(
    test_app_client: TestClient, 
    test_fan_token: str, 
    test_musician: dict, 
    db_session: Session,
    test_fan: dict
):
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id = test_musician["obj_id"]

    res_fav = test_app_client.post(f"/musicos/{musico_id}/favoritar", headers=headers_fan)
    assert res_fav.status_code == 200 
    
    response_desfavoritar = test_app_client.delete(f"/musicos/{musico_id}/favoritar", headers=headers_fan)
    assert response_desfavoritar.status_code == 200, f"Erro ao desfavoritar: {response_desfavoritar.json()}"
    
    data_resposta_desfavoritar = response_desfavoritar.json()
    assert not any(musico["id"] == musico_id for musico in data_resposta_desfavoritar.get("musicos_favoritos", []))

    fan_id = test_fan["id"]
    db_fan = crud.obter_usuario_publico_por_id(db_session, usuario_id=fan_id)
    assert db_fan is not None
    assert not any(musico.id == musico_id for musico in db_fan.musicos_favoritos)


def test_fan_tenta_desfavoritar_musico_nao_favoritado(
    test_app_client: TestClient, test_fan_token: str, test_musician: dict
):
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id = test_musician["obj_id"]

    response = test_app_client.delete(f"/musicos/{musico_id}/favoritar", headers=headers_fan)
    assert response.status_code == 400
    assert response.json()["detail"] == "Músico não está nos seus favoritos"


def test_fan_tenta_favoritar_musico_inexistente(test_app_client: TestClient, test_fan_token: str):
    """Testa um fã tentando favoritar um músico que não existe."""
    headers_fan = {"Authorization": f"Bearer {test_fan_token}"}
    musico_id_inexistente = 99999 

    response = test_app_client.post(f"/musicos/{musico_id_inexistente}/favoritar", headers=headers_fan)
    assert response.status_code == 404
    # CORREÇÃO AQUI:
    assert response.json()["detail"] == "Músico não encontrado ou inativo para favoritar"


def test_acessar_endpoints_favoritos_sem_token_de_fan(
    test_app_client: TestClient, 
    test_musician_token: str,
    test_musician: dict
):
    """Testa acessar endpoints de favoritos sem token de fã (sem token ou com token de músico)."""
    musico_id_qualquer = test_musician["obj_id"]

    response_post_no_token = test_app_client.post(f"/musicos/{musico_id_qualquer}/favoritar")
    assert response_post_no_token.status_code == 401 
    
    response_delete_no_token = test_app_client.delete(f"/musicos/{musico_id_qualquer}/favoritar")
    assert response_delete_no_token.status_code == 401

    headers_musician = {"Authorization": f"Bearer {test_musician_token}"}
    response_post_musician_token = test_app_client.post(f"/musicos/{musico_id_qualquer}/favoritar", headers=headers_musician)
    assert response_post_musician_token.status_code == 403
    assert response_post_musician_token.json()["detail"] == "Acesso não permitido para este tipo de usuário"
    
    response_delete_musician_token = test_app_client.delete(f"/musicos/{musico_id_qualquer}/favoritar", headers=headers_musician)
    assert response_delete_musician_token.status_code == 403
    assert response_delete_musician_token.json()["detail"] == "Acesso não permitido para este tipo de usuário"