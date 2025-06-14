# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Response, Query, File, UploadFile
# Removido StaticFiles se você não for mais servir as fotos de perfil do sistema de arquivos local
# from fastapi.staticfiles import StaticFiles 
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, timezone # Adicionado timezone
from typing import Annotated, List, Optional 
# import shutil # Não será mais necessário se o upload for direto para o GCS
import uuid
import os # Para getenv
from google.cloud import storage # Para interagir com o GCS
# import logging # Opcional

from .database import engine, get_db 
from . import models, schemas, crud
from .security import (
    criar_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    obter_payload_token_musico, obter_payload_token_fan
)
# Removido import datetime duplicado, já que timedelta e timezone foram importados de datetime

# logger = logging.getLogger(__name__) # Opcional

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PalcoApp API",
    description="API para o PalcoApp, conectando músicos e seu público.",
    version="0.1.0",
)

# Removido os.makedirs para app/static/profile_pics se as fotos vão para o GCS
# if not os.path.exists("app/static"):
#     os.makedirs("app/static")
# if not os.path.exists("app/static/profile_pics"):
#     os.makedirs("app/static/profile_pics")

# Removido app.mount para /static se você não estiver servindo outros arquivos estáticos por aqui.
# Se você tiver outros arquivos estáticos (CSS, JS para documentação, etc.) que NÃO são uploads, mantenha.
# app.mount("/static", StaticFiles(directory="app/static"), name="static")


# --- Funções de Dependência para Obter Usuários Logados ---
# ... (seu código obter_musico_logado e obter_usuario_publico_logado permanece o mesmo) ...
async def obter_musico_logado(token_payload: Annotated[schemas.TokenData, Depends(obter_payload_token_musico)], db: Annotated[Session, Depends(get_db)]) -> models.Musico:
    if token_payload.role != "musico": raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não permitido para este tipo de usuário")
    if token_payload.user_id is None: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: user_id não encontrado")
    musico = crud.obter_musico_por_id(db, musico_id=token_payload.user_id)
    if musico is None: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Músico não encontrado para o token fornecido.")
    return musico

async def obter_usuario_publico_logado(token_payload: Annotated[schemas.TokenData, Depends(obter_payload_token_fan)], db: Annotated[Session, Depends(get_db)]) -> models.UsuarioPublico:
    if token_payload.role != "fan": raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não permitido para este tipo de usuário")
    if token_payload.user_id is None: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: user_id não encontrado")
    usuario = crud.obter_usuario_publico_por_id(db, usuario_id=token_payload.user_id)
    if usuario is None: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário (fã) não encontrado para o token fornecido.")
    return usuario


# --- Endpoints de Autenticação ---
# ... (seus endpoints de /token e /usuarios/token permanecem os mesmos) ...
@app.post("/token", response_model=schemas.Token, tags=["Autenticação - Músicos"], summary="Login para Músicos")
async def login_musico_para_obter_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    musico = crud.autenticar_musico(db, email=form_data.username, senha_texto_plano=form_data.password)
    if not musico: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = criar_access_token(data={"sub": musico.email, "user_id": musico.id, "role": "musico"}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user_id": musico.id, "email": musico.email, "role": "musico", "nome_exibicao": musico.nome_artistico}

@app.post("/usuarios/token", response_model=schemas.Token, tags=["Autenticação - Fãs"], summary="Login para Usuários (Fãs)")
async def login_fan_para_obter_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    usuario_publico = crud.autenticar_usuario_publico(db, email=form_data.username, senha_texto_plano=form_data.password)
    if not usuario_publico: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = criar_access_token(data={"sub": usuario_publico.email, "user_id": usuario_publico.id, "role": "fan"}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user_id": usuario_publico.id, "email": usuario_publico.email, "role": "fan", "nome_exibicao": usuario_publico.nome_completo or usuario_publico.email}


# --- Endpoints de Músicos ---
# ... (seu endpoint POST /musicos/ para criar músico permanece o mesmo) ...
@app.post("/musicos/", response_model=schemas.Musico, status_code=status.HTTP_201_CREATED, tags=["Músicos"], summary="Cadastrar um novo músico")
def criar_novo_musico(musico: schemas.MusicoCreate, db: Annotated[Session, Depends(get_db)]):
    db_musico_existente = crud.obter_musico_por_email(db, email=musico.email)
    if db_musico_existente: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registrado")
    novo_musico = crud.criar_musico(db=db, musico=musico)
    return novo_musico

# --- Endpoint de Upload de Foto de Perfil do Músico (MODIFICADO PARA GCS) ---
@app.put(
    "/musicos/me/foto_perfil", 
    response_model=schemas.Musico, # Retorna o perfil do músico atualizado
    tags=["Músicos - Perfil Logado"],
    summary="Upload da foto de perfil do músico logado para GCS",
    description="Permite que o músico autenticado faça upload ou atualize sua foto de perfil, armazenando no Google Cloud Storage."
)
async def upload_foto_perfil_musico_gcs( # Renomeado para clareza
    musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)],
    db: Annotated[Session, Depends(get_db)],
    foto_arquivo: UploadFile = File(..., description="Arquivo da imagem de perfil (jpg, png)") 
):
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    # A variável de ambiente GOOGLE_APPLICATION_CREDENTIALS (com o caminho para a chave JSON)
    # deve ser configurada no ambiente do Render para que storage.Client() funcione automaticamente.
    
    if not GCS_BUCKET_NAME:
        print("[UPLOAD_FOTO_GCS] ERRO FATAL: Variável de ambiente GCS_BUCKET_NAME não configurada no servidor.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Configuração de armazenamento de fotos está incompleta no servidor.")

    try:
        storage_client = storage.Client() # Inicializa o cliente aqui
    except Exception as e_client:
        print(f"[UPLOAD_FOTO_GCS] ERRO FATAL: Não foi possível inicializar o cliente Google Cloud Storage: {e_client}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao conectar com o serviço de armazenamento de fotos.")


    allowed_extensions = {"png", "jpg", "jpeg"}
    original_filename = foto_arquivo.filename if foto_arquivo.filename else "unknown_file"
    file_extension = original_filename.split(".")[-1].lower() if "." in original_filename else ""
    
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tipo de arquivo inválido ({file_extension}). Apenas PNG, JPG, JPEG são permitidos.")

    # Nome do arquivo no GCS (blob name)
    gcs_blob_name = f"profile_pics/user_{musico_logado.id}_{uuid.uuid4()}.{file_extension}"
    url_publica_gcs = ""

    try:
        print(f"[UPLOAD_FOTO_GCS] Bucket: '{GCS_BUCKET_NAME}', Blob: '{gcs_blob_name}', ContentType: {foto_arquivo.content_type}")
        
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_blob_name)
        
        contents = await foto_arquivo.read()
        blob.upload_from_string(contents, content_type=foto_arquivo.content_type)
        
        print(f"[UPLOAD_FOTO_GCS] Upload para GCS bem-sucedido: {gcs_blob_name}")

        # Para tornar o objeto publicamente legível programaticamente (se as permissões do bucket não forem uniformes para public-read)
        # É mais comum definir o bucket como publicamente legível ou usar ACLs de objeto.
        # Se o bucket já está configurado para que novos objetos sejam públicos, esta linha pode não ser necessária
        # ou pode ser controlada ao criar o blob com `blob.make_public()` *antes* do upload ou definindo `predefinedAcl='publicRead'`
        # blob.make_public() 
        # print(f"[UPLOAD_FOTO_GCS] Blob tornado público (se aplicável).")

        url_publica_gcs = blob.public_url 
        print(f"[UPLOAD_FOTO_GCS] URL pública do arquivo no GCS: {url_publica_gcs}")

    except Exception as e:
        print(f"[UPLOAD_FOTO_GCS] ERRO durante o upload para GCS: {e}, Tipo: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Não foi possível fazer upload da foto: {e}")
    finally:
        await foto_arquivo.close() 
    
    # Lógica para deletar foto ANTIGA do GCS (se existir e se for diferente)
    # Esta parte é mais complexa e opcional para uma primeira implementação.
    # Requer que a URL antiga também seja uma URL do GCS para extrair o nome do blob antigo.
    if musico_logado.foto_perfil_url and musico_logado.foto_perfil_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
        if musico_logado.foto_perfil_url != url_publica_gcs: # Só deleta se a URL for diferente
            try:
                # Extrai o nome do blob da URL antiga
                # Ex: https://storage.googleapis.com/meu-bucket/profile_pics/arquivo.jpg -> profile_pics/arquivo.jpg
                old_blob_name_parts = musico_logado.foto_perfil_url.split(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/")
                if len(old_blob_name_parts) > 1:
                    old_blob_name = old_blob_name_parts[1].split("?")[0] # Remove query params se houver
                    if old_blob_name: # Garante que não está vazio
                        old_bucket_to_delete_from = storage_client.bucket(GCS_BUCKET_NAME)
                        old_blob_to_delete = old_bucket_to_delete_from.blob(old_blob_name)
                        if old_blob_to_delete.exists(): # Verifica se o blob antigo existe antes de tentar deletar
                            old_blob_to_delete.delete()
                            print(f"[UPLOAD_FOTO_GCS] Foto antiga '{old_blob_name}' deletada do GCS.")
                        else:
                            print(f"[UPLOAD_FOTO_GCS] Foto antiga '{old_blob_name}' não encontrada no GCS para deletar.")
            except Exception as e_del:
                print(f"[UPLOAD_FOTO_GCS] Erro ao tentar deletar foto antiga do GCS '{musico_logado.foto_perfil_url}': {e_del}")
                # Não relança a exceção aqui, pois o upload da nova foto foi o principal.

    musico_atualizado = crud.atualizar_foto_perfil_musico(db, musico_id=musico_logado.id, foto_url=url_publica_gcs)
    if not musico_atualizado:
        # Se o crud falhar, idealmente o arquivo no GCS deveria ser revertido/deletado, mas isso adiciona complexidade.
        # Por enquanto, focamos em atualizar o banco.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível atualizar o perfil do músico no banco com a nova foto.")
    
    print(f"[UPLOAD_FOTO_GCS] URL da foto atualizada no banco para músico ID {musico_logado.id}: {url_publica_gcs}")
    return musico_atualizado

# ... (Restante dos seus endpoints de músicos, repertório, shows, usuários, favoritos, pedidos, etc., permanecem os mesmos) ...
# Exemplo:
@app.get("/musicos/me/", response_model=schemas.Musico, tags=["Músicos - Perfil Logado"], summary="Obter perfil do músico logado")
async def ler_musico_logado(musico_atual: Annotated[models.Musico, Depends(obter_musico_logado)]):
    return musico_atual

@app.put("/musicos/me/", response_model=schemas.Musico, tags=["Músicos - Perfil Logado"], summary="Atualizar perfil do músico logado (sem foto)")
async def atualizar_perfil_musico_logado(musico_update_payload: schemas.MusicoUpdate, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]):
    # Este endpoint agora só atualiza dados textuais. A foto é por /musicos/me/foto_perfil
    musico_atualizado = crud.atualizar_musico(db=db, musico_db_obj=musico_logado, musico_update_data=musico_update_payload)
    return musico_atualizado

# --- Rota Raiz ---
@app.get("/", tags=["Geral"], summary="Endpoint Raiz da API")
async def root(): return {"message": "Bem-vindo ao PalcoApp API! O cérebro está funcionando!"}

# --- Rota de Itens (Exemplo) ---
@app.get("/items/{item_id}", tags=["Geral - Exemplo"], include_in_schema=False, summary="Exemplo de rota com parâmetro")
async def read_item(item_id: int, q: Optional[str] = None): return {"item_id": item_id, "q": q}