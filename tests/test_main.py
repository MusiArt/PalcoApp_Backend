# tests/test_main.py
from fastapi.testclient import TestClient
# Não importamos 'app' diretamente, pois a fixture 'test_app_client' já a configura.

# O Pytest injetará automaticamente a fixture 'test_app_client' definida em conftest.py
# se um parâmetro de função de teste tiver o mesmo nome.

def test_read_main_root(test_app_client: TestClient): # Nome da fixture corrigido para test_app_client
    """Testa se o endpoint raiz ('/') está funcionando corretamente."""
    
    # Faz uma requisição GET para o endpoint "/" usando o cliente de teste
    response = test_app_client.get("/") # Variável da fixture corrigida para test_app_client
    
    # Verifica se o código de status HTTP da resposta é 200 (OK)
    assert response.status_code == 200
    
    # Verifica se o corpo da resposta JSON é o esperado
    assert response.json() == {"message": "Bem-vindo ao PalcoApp API! O cérebro está funcionando!"}

# Você pode adicionar mais testes neste arquivo no futuro, por exemplo:
# def test_create_musician(test_app_client: TestClient, db_test_session: SQLAlchemySession):
#     # ... seu código de teste para criar um músico ...
#     pass