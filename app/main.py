# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Response, Query, File, UploadFile
# from fastapi.staticfiles import StaticFiles # REMOVIDO se as fotos de perfil vão SÓ para o GCS
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, timezone 
from typing import Annotated, List, Optional 
# import shutil # REMOVIDO - Não vamos mais salvar localmente com shutil
import uuid
import os 
from google.cloud import storage # IMPORTADO para interagir com o GCS

from .database import engine, get_db 
from . import models, schemas, crud
from .security import (
    criar_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    obter_payload_token_musico, obter_payload_token_fan
)
# import datetime # Removido import datetime duplicado

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PalcoApp API",
    description="API para o PalcoApp, conectando músicos e seu público.",
    version="0.1.0",
)

# REMOVIDO os.makedirs para app/static/profile_pics
# REMOVIDO app.mount("/static", ...) se você não tiver OUTROS arquivos estáticos sendo servidos por ele.
# Se você tiver, por exemplo, CSS/JS para a documentação do FastAPI que estão em app/static,
# então você pode manter o app.mount, mas ele não será mais usado para as fotos de perfil.
# Para simplificar, vou remover por agora, assumindo que as fotos de perfil são os únicos "estáticos dinâmicos".
# Se precisar de volta para outros arquivos, me avise.


# --- Funções de Dependência para Obter Usuários Logados ---
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
@app.post("/musicos/", response_model=schemas.Musico, status_code=status.HTTP_201_CREATED, tags=["Músicos"], summary="Cadastrar um novo músico")
def criar_novo_musico(musico: schemas.MusicoCreate, db: Annotated[Session, Depends(get_db)]):
    db_musico_existente = crud.obter_musico_por_email(db, email=musico.email)
    if db_musico_existente: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registrado")
    novo_musico = crud.criar_musico(db=db, musico=musico)
    return novo_musico
    
@app.get(
    "/musicos/", 
    response_model=List[schemas.MusicoPublicProfile], 
    tags=["Músicos - Público"],
    summary="Listar músicos (perfis públicos)",
    description="Retorna uma lista paginada de músicos ativos. Pode ser filtrado por nome artístico e/ou gênero."
)
def ler_musicos_publico(
    db: Annotated[Session, Depends(get_db)], 
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = Query(default=None, min_length=1, max_length=50, description="Termo para buscar no nome artístico do músico (case-insensitive)"),
    genero: Optional[str] = Query(default=None, min_length=1, max_length=50, description="Filtrar músicos por um gênero musical específico (case-insensitive, busca por 'contém')")
):
    musicos = crud.obter_musicos(db, skip=skip, limit=limit, search_term=search, genero_filter=genero) 
    return musicos

@app.get("/musicos/{musico_id}", response_model=schemas.MusicoPublicProfile, tags=["Músicos - Público"], summary="Obter perfil público de um músico específico")
def ler_musico_especifico_publico(musico_id: int, db: Annotated[Session, Depends(get_db)]):
    db_musico = crud.obter_musico_por_id(db, musico_id=musico_id)
    if db_musico is None or not db_musico.is_active : raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Músico não encontrado ou inativo")
    return db_musico

@app.get("/musicos/me/", response_model=schemas.Musico, tags=["Músicos - Perfil Logado"], summary="Obter perfil do músico logado")
async def ler_musico_logado(musico_atual: Annotated[models.Musico, Depends(obter_musico_logado)]):
    return musico_atual

@app.put("/musicos/me/", response_model=schemas.Musico, tags=["Músicos - Perfil Logado"], summary="Atualizar perfil do músico logado (dados textuais)")
async def atualizar_perfil_musico_logado_textual( # Renomeado para diferenciar do upload de foto
    musico_update_payload: schemas.MusicoUpdate, 
    musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], 
    db: Annotated[Session, Depends(get_db)]
):
    musico_atualizado = crud.atualizar_musico(db=db, musico_db_obj=musico_logado, musico_update_data=musico_update_payload)
    return musico_atualizado

# --- MODIFICADO PARA USAR GOOGLE CLOUD STORAGE ---
@app.put(
    "/musicos/me/foto_perfil", 
    response_model=schemas.Musico,
    tags=["Músicos - Perfil Logado"],
    summary="Upload da foto de perfil do músico logado para GCS",
    description="Permite que o músico autenticado faça upload ou atualize sua foto de perfil, armazenando no Google Cloud Storage."
)
async def upload_foto_perfil_musico_gcs( 
    musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)],
    db: Annotated[Session, Depends(get_db)],
    foto_arquivo: UploadFile = File(..., description="Arquivo da imagem de perfil (jpg, png)") 
):
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    # GOOGLE_APPLICATION_CREDENTIALS deve estar configurado no ambiente do Render
    
    if not GCS_BUCKET_NAME:
        print("[UPLOAD_FOTO_GCS] ERRO FATAL: Variável de ambiente GCS_BUCKET_NAME não configurada.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Configuração de armazenamento de fotos incompleta (bucket).")

    try:
        storage_client = storage.Client()
        print("[UPLOAD_FOTO_GCS] Cliente Google Cloud Storage inicializado.")
    except Exception as e_client:
        print(f"[UPLOAD_FOTO_GCS] ERRO FATAL ao inicializar cliente GCS: {e_client}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao conectar com o serviço de armazenamento de fotos.")

    allowed_extensions = {"png", "jpg", "jpeg"}
    original_filename = foto_arquivo.filename if foto_arquivo.filename else "unknown_file.tmp"
    file_extension = original_filename.split(".")[-1].lower() if "." in original_filename else "tmp"
    
    if file_extension not in allowed_extensions:
        print(f"[UPLOAD_FOTO_GCS] ERRO: Tipo de arquivo inválido: {file_extension}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tipo de arquivo inválido ({file_extension}). Apenas PNG, JPG, JPEG.")

    gcs_blob_name = f"profile_pics/user_{musico_logado.id}_{uuid.uuid4()}.{file_extension}"
    url_publica_gcs = ""

    try:
        print(f"[UPLOAD_FOTO_GCS] Preparando upload para Bucket: '{GCS_BUCKET_NAME}', Blob: '{gcs_blob_name}', ContentType: {foto_arquivo.content_type}")
        
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_blob_name)
        
        contents = await foto_arquivo.read()
        blob.upload_from_string(contents, content_type=foto_arquivo.content_type) # Faz o upload
        
        print(f"[UPLOAD_FOTO_GCS] Upload para GCS de '{gcs_blob_name}' BEM-SUCEDIDO.")

        # Torna o blob publicamente legível (IMPORTANTE se o bucket não tiver essa política por padrão)
        # Se você já configurou o bucket para que TODOS os novos objetos sejam públicos, isso pode não ser estritamente necessário
        # ou pode até dar erro se as permissões do bucket forem uniformes e não permitirem ACLs por objeto.
        # Teste primeiro sem isso se o bucket já for public-read. Se as imagens não carregarem, adicione.
        try:
            blob.make_public()
            print(f"[UPLOAD_FOTO_GCS] Blob '{gcs_blob_name}' tornado público.")
        except Exception as e_public:
            print(f"[UPLOAD_FOTO_GCS] AVISO: Não foi possível tornar o blob '{gcs_blob_name}' público programaticamente: {e_public}. Verifique as permissões do bucket (deve ser 'Uniform' com 'allUsers' como 'Storage Object Viewer').")
            # Se o bucket já é public-read, esta exceção pode ser ignorada, a URL pública ainda deve funcionar.

        url_publica_gcs = blob.public_url 
        print(f"[UPLOAD_FOTO_GCS] URL pública obtida do GCS: {url_publica_gcs}")

    except Exception as e_upload:
        print(f"[UPLOAD_FOTO_GCS] ERRO CRÍTICO durante o upload para GCS: {e_upload}, Tipo: {type(e_upload)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Não foi possível concluir o upload da foto: {e_upload}")
    finally:
        await foto_arquivo.close() 
    
    # Lógica para deletar foto ANTIGA do GCS (Opcional, mas recomendado)
    if musico_logado.foto_perfil_url and musico_logado.foto_perfil_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
        if musico_logado.foto_perfil_url != url_publica_gcs:
            try:
                old_blob_name_parts = musico_logado.foto_perfil_url.split(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/")
                if len(old_blob_name_parts) > 1:
                    old_blob_name = old_blob_name_parts[1].split("?")[0] 
                    if old_blob_name: 
                        old_bucket_to_delete_from = storage_client.bucket(GCS_BUCKET_NAME)
                        old_blob_to_delete = old_bucket_to_delete_from.blob(old_blob_name)
                        if old_blob_to_delete.exists(storage_client): # Passar o cliente pode ser necessário em algumas versões
                            old_blob_to_delete.delete(client=storage_client) # Passar o cliente pode ser necessário
                            print(f"[UPLOAD_FOTO_GCS] Foto antiga '{old_blob_name}' deletada do GCS.")
                        else:
                            print(f"[UPLOAD_FOTO_GCS] Foto antiga '{old_blob_name}' não encontrada no GCS para deletar (URL no BD: {musico_logado.foto_perfil_url}).")
            except Exception as e_del_gcs:
                print(f"[UPLOAD_FOTO_GCS] AVISO: Erro ao tentar deletar foto antiga do GCS '{musico_logado.foto_perfil_url}': {e_del_gcs}")

    musico_atualizado = crud.atualizar_foto_perfil_musico(db, musico_id=musico_logado.id, foto_url=url_publica_gcs)
    if not musico_atualizado:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível atualizar o perfil do músico no banco com a nova URL da foto.")
    
    print(f"[UPLOAD_FOTO_GCS] URL da foto '{url_publica_gcs}' atualizada no banco para músico ID {musico_logado.id}.")
    return musico_atualizado

# ... (Restante dos seus endpoints de repertório, shows, usuários (Fãs), favoritos, pedidos, etc., permanecem os mesmos que você me enviou) ...

# --- Rota Raiz ---
@app.get("/", tags=["Geral"], summary="Endpoint Raiz da API")
async def root(): return {"message": "Bem-vindo ao PalcoApp API! O cérebro está funcionando!"}

# --- Rota de Itens (Exemplo) ---
@app.get("/items/{item_id}", tags=["Geral - Exemplo"], include_in_schema=False, summary="Exemplo de rota com parâmetro")
async def read_item(item_id: int, q: Optional[str] = None): return {"item_id": item_id, "q": q}