# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Response, Query, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Annotated, List, Optional # Garanta que Optional e List estão aqui
import shutil
import uuid

from .database import engine, get_db # Usando seu get_db
from . import models, schemas, crud
from .security import (
    criar_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    obter_payload_token_musico, obter_payload_token_fan
)
import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PalcoApp API",
    description="API para o PalcoApp, conectando músicos e seu público.",
    version="0.1.0",
)

import os
if not os.path.exists("app/static"):
    os.makedirs("app/static")
if not os.path.exists("app/static/profile_pics"):
    os.makedirs("app/static/profile_pics")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Isso significa que arquivos dentro de 'app/static/' estarão acessíveis via '/static/...' na URL
# Ex: app/static/profile_pics/imagem.jpg -> http://127.0.0.1:8000/static/profile_pics/imagem.jpg

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
    # --- INÍCIO DOS PRINTS DE DEPURAÇÃO (PARA MÚSICOS) ---
    print("----------------------------------------------------")
    print(f"[MAIN.PY - login_musico_para_obter_token] Tentativa de login recebida.")
    print(f"[MAIN.PY - login_musico_para_obter_token] Email (form_data.username) recebido: '{form_data.username}'")
    # CUIDADO: O print abaixo mostra a senha. Use APENAS para depuração e REMOVA depois!
    # print(f"[MAIN.PY - login_musico_para_obter_token] Senha (form_data.password) recebida: '{form_data.password}'")
    print("----------------------------------------------------")
    # --- FIM DOS PRINTS DE DEPURAÇÃO (PARA MÚSICOS) ---

    musico = crud.autenticar_musico(db, email=form_data.username, senha_texto_plano=form_data.password)

    # --- INÍCIO DOS PRINTS APÓS CHAMAR crud.autenticar_musico ---
    print("----------------------------------------------------")
    if musico:
        print(f"[MAIN.PY - login_musico_para_obter_token] A função crud.autenticar_musico RETORNOU um músico (sucesso).")
        print(f"[MAIN.PY - login_musico_para_obter_token] Detalhes do músico autenticado: ID={musico.id}, Email='{musico.email}', Nome Artístico='{musico.nome_artistico}'")
    else:
        print(f"[MAIN.PY - login_musico_para_obter_token] A função crud.autenticar_musico NÃO retornou um músico (falha na autenticação).")
    print("----------------------------------------------------")
    # --- FIM DOS PRINTS APÓS CHAMAR crud.autenticar_musico ---
    
    if not musico: 
        print(f"[MAIN.PY - login_musico_para_obter_token] Músico não autenticado. Levantando HTTPException 401.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    
    print(f"[MAIN.PY - login_musico_para_obter_token] Autenticação bem-sucedida para músico. Criando token de acesso para ID: {musico.id}.")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = criar_access_token(data={"sub": musico.email, "user_id": musico.id, "role": "musico"}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user_id": musico.id, "email": musico.email, "role": "musico", "nome_exibicao": musico.nome_artistico}

@app.post("/usuarios/token", response_model=schemas.Token, tags=["Autenticação - Fãs"], summary="Login para Usuários (Fãs)")
async def login_fan_para_obter_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    # --- INÍCIO DOS PRINTS DE DEPURAÇÃO (PARA FÃS) ---
    print("----------------------------------------------------")
    print(f"[MAIN.PY - login_fan_para_obter_token] Tentativa de login recebida.")
    print(f"[MAIN.PY - login_fan_para_obter_token] Email (form_data.username) recebido: '{form_data.username}'")
    # CUIDADO: O print abaixo mostra a senha. Use APENAS para depuração e REMOVA depois!
    # print(f"[MAIN.PY - login_fan_para_obter_token] Senha (form_data.password) recebida: '{form_data.password}'")
    print("----------------------------------------------------")
    # --- FIM DOS PRINTS DE DEPURAÇÃO (PARA FÃS) ---

    usuario_publico = crud.autenticar_usuario_publico(db, email=form_data.username, senha_texto_plano=form_data.password)
    
    # --- INÍCIO DOS PRINTS APÓS CHAMAR crud.autenticar_usuario_publico ---
    print("----------------------------------------------------")
    if usuario_publico:
        print(f"[MAIN.PY - login_fan_para_obter_token] A função crud.autenticar_usuario_publico RETORNOU um usuário (sucesso).")
        print(f"[MAIN.PY - login_fan_para_obter_token] Detalhes do usuário autenticado: ID={usuario_publico.id}, Email='{usuario_publico.email}', Nome='{usuario_publico.nome_completo}'")
    else:
        print(f"[MAIN.PY - login_fan_para_obter_token] A função crud.autenticar_usuario_publico NÃO retornou um usuário (falha na autenticação).")
    print("----------------------------------------------------")
    # --- FIM DOS PRINTS APÓS CHAMAR crud.autenticar_usuario_publico ---

    if not usuario_publico: 
        print(f"[MAIN.PY - login_fan_para_obter_token] Usuário (fã) não autenticado. Levantando HTTPException 401.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    
    print(f"[MAIN.PY - login_fan_para_obter_token] Autenticação bem-sucedida para fã. Criando token de acesso para ID: {usuario_publico.id}.")
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
    description="Retorna uma lista paginada de músicos ativos. Pode ser filtrado por nome artístico e/ou gênero." # Descrição atualizada
)
def ler_musicos_publico(
    db: Annotated[Session, Depends(get_db)], 
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = Query(
        default=None, 
        min_length=1, 
        max_length=50, 
        description="Termo para buscar no nome artístico do músico (case-insensitive)"
    ),
    genero: Optional[str] = Query( # <--- NOVO PARÂMETRO ADICIONADO
        default=None,
        min_length=1,
        max_length=50, 
        description="Filtrar músicos por um gênero musical específico (case-insensitive, busca por 'contém')"
    )
):
    if search: 
        print(f"API GET /musicos/ - Recebido termo de busca: '{search}'")
    if genero: # <--- LOG PARA O NOVO PARÂMETRO
        print(f"API GET /musicos/ - Recebido filtro de gênero: '{genero}'")
    
    musicos = crud.obter_musicos(
        db, 
        skip=skip, 
        limit=limit, 
        search_term=search, 
        genero_filter=genero # <--- PASSANDO O NOVO PARÂMETRO PARA A FUNÇÃO CRUD
    ) 
    return musicos

@app.get("/musicos/{musico_id}", response_model=schemas.MusicoPublicProfile, tags=["Músicos - Público"], summary="Obter perfil público de um músico específico")
def ler_musico_especifico_publico(musico_id: int, db: Annotated[Session, Depends(get_db)]):
    db_musico = crud.obter_musico_por_id(db, musico_id=musico_id)
    if db_musico is None or not db_musico.is_active : raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Músico não encontrado ou inativo")
    return db_musico

@app.get("/musicos/me/", response_model=schemas.Musico, tags=["Músicos - Perfil Logado"], summary="Obter perfil do músico logado")
async def ler_musico_logado(musico_atual: Annotated[models.Musico, Depends(obter_musico_logado)]):
    return musico_atual

@app.put("/musicos/me/", response_model=schemas.Musico, tags=["Músicos - Perfil Logado"], summary="Atualizar perfil do músico logado")
async def atualizar_perfil_musico_logado(musico_update_payload: schemas.MusicoUpdate, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]):
    musico_atualizado = crud.atualizar_musico(db=db, musico_db_obj=musico_logado, musico_update_data=musico_update_payload)
    return musico_atualizado

@app.put(
    "/musicos/me/foto_perfil", 
    response_model=schemas.Musico, # Retorna o perfil do músico atualizado
    tags=["Músicos - Perfil Logado"],
    summary="Upload da foto de perfil do músico logado",
    description="Permite que o músico autenticado faça upload ou atualize sua foto de perfil."
)
async def upload_foto_perfil_musico(
    musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)],
    db: Annotated[Session, Depends(get_db)],
    foto_arquivo: UploadFile = File(..., description="Arquivo da imagem de perfil (jpg, png)") 
    # O "File(...)" torna este parâmetro parte do corpo da requisição como um upload de arquivo
):
    # Validação simples do tipo de arquivo (pode ser mais robusta)
    allowed_extensions = {"png", "jpg", "jpeg"}
    file_extension = foto_arquivo.filename.split(".")[-1].lower() if "." in foto_arquivo.filename else ""
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de arquivo inválido. Apenas PNG, JPG, JPEG são permitidos.")

    # Gerar um nome de arquivo único para evitar conflitos e por segurança
    # Ex: user_IDDOMUSICO_UUID.extensao
    unique_filename_base = f"user_{musico_logado.id}_{uuid.uuid4()}"
    filename_with_ext = f"{unique_filename_base}.{file_extension}"
    
    file_path_on_server = f"app/static/profile_pics/{filename_with_ext}"
    url_path_for_db = f"static/profile_pics/{filename_with_ext}" # Caminho a ser salvo no DB

    try:
        # Salvar o arquivo no servidor
        with open(file_path_on_server, "wb") as buffer:
            shutil.copyfileobj(foto_arquivo.file, buffer)
    except Exception as e:
        print(f"Erro ao salvar arquivo de foto: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível salvar a foto de perfil.")
    finally:
        await foto_arquivo.close() # Sempre feche o arquivo após o uso

    # Se o músico já tinha uma foto, podemos deletar a antiga do sistema de arquivos (opcional)
    if musico_logado.foto_perfil_url:
        old_file_path = f"app/{musico_logado.foto_perfil_url}" # Assume que a URL no DB é relativa a 'app/'
        if os.path.exists(old_file_path) and old_file_path != file_path_on_server : # Não deleta se for o mesmo arquivo por algum motivo
            try:
                os.remove(old_file_path)
                print(f"Foto de perfil antiga '{old_file_path}' deletada.")
            except Exception as e_del:
                print(f"Erro ao deletar foto antiga '{old_file_path}': {e_del}")
                # Não lança exceção aqui, pois o upload da nova foi bem-sucedido.

    # Atualizar o caminho da foto no banco de dados para o músico
    musico_atualizado = crud.atualizar_foto_perfil_musico(db, musico_id=musico_logado.id, foto_url=url_path_for_db)
    if not musico_atualizado:
        # Isso não deveria acontecer se o musico_logado é válido
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível atualizar o perfil do músico com a nova foto.")
    
    print(f"Foto de perfil para músico ID {musico_logado.id} atualizada para: {url_path_for_db}")
    return musico_atualizado # Retorna o músico com a URL da foto atualizada
#                                ***** FIM DO NOVO ENDPOINT *****

# --- Endpoints de Repertório ---
@app.post("/repertorio/", response_model=schemas.ItemRepertorio, status_code=status.HTTP_201_CREATED, tags=["Repertório"], summary="Adicionar item ao repertório")
async def adicionar_item_ao_repertorio(item_repertorio: schemas.ItemRepertorioCreate, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]): 
    return crud.criar_item_repertorio_para_musico(db=db, item=item_repertorio, musico_id=musico_logado.id)

@app.get("/repertorio/", response_model=List[schemas.ItemRepertorio], tags=["Repertório"], summary="Listar repertório do músico logado")
async def ler_repertorio_do_musico_logado(musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100): 
    return crud.obter_itens_repertorio_do_musico(db=db, musico_id=musico_logado.id, skip=skip, limit=limit)

@app.put("/repertorio/{item_id}", response_model=schemas.ItemRepertorio, tags=["Repertório"], summary="Atualizar item do repertório")
async def atualizar_item_de_repertorio(item_id: int, item_update_data: schemas.ItemRepertorioUpdate, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]): 
    item_atualizado = crud.atualizar_item_repertorio_do_musico(db=db, item_id=item_id, musico_id=musico_logado.id, item_update=item_update_data)
    if item_atualizado is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de repertório não encontrado ou não pertence ao músico")
    return item_atualizado

@app.delete("/repertorio/{item_id}", tags=["Repertório"], summary="Deletar item do repertório", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_item_de_repertorio(item_id: int, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]): 
    item_deletado = crud.deletar_item_repertorio_do_musico(db=db, item_id=item_id, musico_id=musico_logado.id)
    if item_deletado is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de repertório não encontrado ou não pertence ao músico")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Endpoints de Shows ---
@app.post("/shows/", response_model=schemas.Show, status_code=status.HTTP_201_CREATED, tags=["Shows"], summary="Criar novo show (músico logado)")
async def criar_novo_show(show_data: schemas.ShowCreate, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]):
    return crud.criar_show_para_musico(db=db, show=show_data, musico_id=musico_logado.id)

@app.get("/shows/me/", response_model=List[schemas.Show], tags=["Shows - Músico Logado"], summary="Listar shows do músico logado")
async def ler_shows_do_musico_logado(musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100):
    return crud.obter_shows_do_musico(db=db, musico_id=musico_logado.id, skip=skip, limit=limit)

@app.get(
    "/shows/", 
    response_model=List[schemas.Show], 
    tags=["Shows - Público"],
    summary="Listar todos os shows (público)",
    description="Retorna uma lista paginada de todos os shows futuros de todos os músicos, incluindo informações do músico. Pode ser filtrado por data."
)
def ler_todos_os_shows_publico(
    db: Annotated[Session, Depends(get_db)], 
    skip: int = 0, 
    limit: int = 100,
    # ***** NOVO PARÂMETRO DE FILTRO DE DATA *****
    data_especifica: Optional[datetime.date] = Query( # Usando datetime.date para o tipo
        default=None,
        description="Filtrar shows por uma data específica (YYYY-MM-DD). Se não fornecido, lista todos os futuros."
    )
    # ***** FIM DO NOVO PARÂMETRO *****
):
    if data_especifica: 
        print(f"API GET /shows/ - Recebido filtro de data_especifica: '{data_especifica}'")
    
    shows = crud.obter_todos_os_shows(
        db=db, 
        skip=skip, 
        limit=limit, 
        data_filtro=data_especifica # Passa o novo filtro para a função CRUD
    )
    return shows

# CORRIGIDO: 'Annotated' no parâmetro db da linha 126 da sua imagem
@app.get("/musicos/{musico_id}/shows/", response_model=List[schemas.Show], tags=["Shows - Público"], summary="Listar shows de um músico específico (público)")
def ler_shows_de_um_musico_especifico_publico(musico_id: int, db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100):
    musico = crud.obter_musico_por_id(db, musico_id=musico_id)
    if not musico or not musico.is_active: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Músico não encontrado ou inativo")
    return crud.obter_shows_do_musico(db=db, musico_id=musico_id, skip=skip, limit=limit)

@app.get(
    "/shows/{show_id}", 
    response_model=schemas.Show, 
    tags=["Shows - Público", "Shows - Detalhes"], # Pode adicionar mais tags se quiser
    summary="Obter detalhes de um show específico",
    description="Retorna os detalhes completos de um show específico pelo seu ID, incluindo informações do músico."
)
def ler_detalhes_do_show(
    show_id: int, 
    db: Annotated[Session, Depends(get_db)]
):
    print(f"API GET /shows/{show_id} - Recebido pedido para show ID: {show_id}")
    db_show = crud.obter_show_por_id(db, show_id=show_id)
    if db_show is None:
        print(f"API GET /shows/{show_id} - Show ID: {show_id} não encontrado.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Show não encontrado")
    
    # Se o show for encontrado, o Pydantic o converterá para schemas.Show automaticamente
    # já que o crud.obter_show_por_id já faz o joinedload do músico.
    print(f"API GET /shows/{show_id} - Show encontrado: {db_show.local_nome}")
    return db_show

# CORRIGIDO: 'Annotated' nos parâmetros musico_logado e db da linha 128 da sua imagem
@app.put("/shows/{show_id}", response_model=schemas.Show, tags=["Shows"], summary="Atualizar show (músico logado)")
async def atualizar_show(show_id: int, show_update_payload: schemas.ShowUpdate, 
                         musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], 
                         db: Annotated[Session, Depends(get_db)]):
    show_atualizado = crud.atualizar_show_do_musico(db=db, show_id=show_id, musico_id=musico_logado.id, show_update_data=show_update_payload)
    if show_atualizado is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Show não encontrado ou não pertence ao músico")
    return show_atualizado

# CORRIGIDO: 'Annotated' nos parâmetros musico_logado e db (se aplicável, não visível na imagem, mas provável)
@app.delete("/shows/{show_id}", tags=["Shows"], summary="Deletar show (músico logado)", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_show(show_id: int, 
                       musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], 
                       db: Annotated[Session, Depends(get_db)]):
    show_deletado = crud.deletar_show_do_musico(db=db, show_id=show_id, musico_id=musico_logado.id)
    if show_deletado is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Show não encontrado ou não pertence ao músico")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Endpoints para UsuarioPublico (Fãs) ---
@app.post("/usuarios/", response_model=schemas.UsuarioPublico, status_code=status.HTTP_201_CREATED, tags=["Usuários (Fãs)"], summary="Cadastrar novo usuário (fã)")
def criar_novo_usuario_publico(usuario_data: schemas.UsuarioPublicoCreate, db: Annotated[Session, Depends(get_db)]):
    db_usuario_existente = crud.obter_usuario_publico_por_email(db, email=usuario_data.email)
    if db_usuario_existente: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registrado para um usuário")
    return crud.criar_usuario_publico(db=db, usuario=usuario_data)

@app.get("/usuarios/me/", response_model=schemas.UsuarioPublico, tags=["Usuários (Fãs) - Perfil Logado"], summary="Obter perfil do usuário (fã) logado")
async def ler_usuario_publico_logado(usuario_atual: Annotated[models.UsuarioPublico, Depends(obter_usuario_publico_logado)]):
    return usuario_atual

@app.put(
    "/usuarios/me/", 
    response_model=schemas.UsuarioPublico, # Retorna o perfil do fã atualizado
    tags=["Usuários (Fãs) - Perfil Logado"],
    summary="Atualizar perfil do usuário (fã) logado",
    description="Permite que o fã autenticado atualize seus dados de perfil (ex: nome completo)."
)
async def atualizar_perfil_usuario_logado(
    usuario_update_payload: schemas.UsuarioPublicoUpdate, 
    usuario_logado: Annotated[models.UsuarioPublico, Depends(obter_usuario_publico_logado)], 
    db: Annotated[Session, Depends(get_db)]
):
    # Log para ver o payload recebido
    print(f"API PUT /usuarios/me/ - Payload recebido: {usuario_update_payload.model_dump(exclude_unset=True)}")
    
    if not usuario_update_payload.model_dump(exclude_unset=True): # Verifica se o payload não está vazio
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum dado fornecido para atualização."
        )

    usuario_atualizado = crud.atualizar_usuario_publico(
        db=db, 
        usuario_db_obj=usuario_logado, 
        usuario_update_data=usuario_update_payload
    )
    print(f"API PUT /usuarios/me/ - Usuário ID {usuario_atualizado.id} atualizado. Novo nome_exibicao para token: {usuario_atualizado.nome_completo or usuario_atualizado.email}")
    # Nota: O token JWT não é reemitido aqui. O nome_exibicao no token existente
    # permanecerá o antigo até o próximo login. A UI no Flutter pegará o nome atualizado do AuthProvider.
    return usuario_atualizado

# --- Endpoints de Favoritos ---
@app.post("/musicos/{musico_id}/favoritar", response_model=schemas.UsuarioPublico, tags=["Favoritos"], summary="Favoritar um músico (fã logado)")
async def favoritar_musico(musico_id: int, usuario_logado: Annotated[models.UsuarioPublico, Depends(obter_usuario_publico_logado)], db: Annotated[Session, Depends(get_db)]):
    musico_a_favoritar = crud.obter_musico_por_id(db, musico_id=musico_id)
    if not musico_a_favoritar or not musico_a_favoritar.is_active: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Músico não encontrado ou inativo para favoritar")
    if crud.verificar_se_musico_e_favorito(db, usuario_id=usuario_logado.id, musico_id=musico_id): raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Músico já está nos seus favoritos")
    return crud.adicionar_musico_aos_favoritos(db, usuario=usuario_logado, musico=musico_a_favoritar)

@app.delete("/musicos/{musico_id}/favoritar", response_model=schemas.UsuarioPublico, tags=["Favoritos"], summary="Desfavoritar um músico (fã logado)")
async def desfavoritar_musico(musico_id: int, usuario_logado: Annotated[models.UsuarioPublico, Depends(obter_usuario_publico_logado)], db: Annotated[Session, Depends(get_db)]):
    musico_a_desfavoritar = crud.obter_musico_por_id(db, musico_id=musico_id)
    if not musico_a_desfavoritar: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Músico não encontrado")
    if not crud.verificar_se_musico_e_favorito(db, usuario_id=usuario_logado.id, musico_id=musico_id): raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Músico não está nos seus favoritos")
    return crud.remover_musico_dos_favoritos(db, usuario=usuario_logado, musico=musico_a_desfavoritar)

# --- Endpoints para Pedidos de Música ---
@app.post("/pedidos/", response_model=schemas.PedidoMusica, status_code=status.HTTP_201_CREATED, tags=["Pedidos de Música"], summary="Fazer um pedido de música (fã logado)")
async def criar_novo_pedido_de_musica(pedido_data: schemas.PedidoMusicaCreate, solicitante: Annotated[models.UsuarioPublico, Depends(obter_usuario_publico_logado)], db: Annotated[Session, Depends(get_db)]):
    musico_destinatario = crud.obter_musico_por_id(db, musico_id=pedido_data.musico_id)
    if not musico_destinatario or not musico_destinatario.is_active: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Músico destinatário não encontrado ou inativo")
    item_repertorio = crud.obter_item_repertorio_do_musico_por_id(db, item_id=pedido_data.item_repertorio_id, musico_id=pedido_data.musico_id)
    if not item_repertorio: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de repertório não encontrado ou não pertence ao músico especificado")
    return crud.criar_pedido_musica(db=db, pedido_data=pedido_data, solicitante_id=solicitante.id)

@app.get("/musicos/me/pedidos/", response_model=List[schemas.PedidoMusica], tags=["Pedidos de Música"], summary="Listar pedidos recebidos (músico logado)")
async def ler_pedidos_recebidos_pelo_musico(musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100):
    return crud.obter_pedidos_para_musico(db=db, musico_id=musico_logado.id, skip=skip, limit=limit)

@app.get("/usuarios/me/pedidos/", response_model=List[schemas.PedidoMusica], tags=["Pedidos de Música"], summary="Listar pedidos feitos (fã logado)")
async def ler_pedidos_feitos_pelo_fan(fan_logado: Annotated[models.UsuarioPublico, Depends(obter_usuario_publico_logado)], db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100):
    return crud.obter_pedidos_feitos_por_fan(db=db, solicitante_id=fan_logado.id, skip=skip, limit=limit)

@app.patch("/pedidos/{pedido_id}/status", response_model=schemas.PedidoMusica, tags=["Pedidos de Música"], summary="Atualizar status de um pedido (músico logado)")
async def atualizar_status_do_pedido(pedido_id: int, status_update: schemas.PedidoMusicaUpdateStatus, musico_logado: Annotated[models.Musico, Depends(obter_musico_logado)], db: Annotated[Session, Depends(get_db)]):
    pedido_db = crud.obter_pedido_musica_por_id(db, pedido_id=pedido_id, musico_id=musico_logado.id)
    if not pedido_db: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado ou não pertence a este músico")
    if status_update.status_pedido not in ["pendente", "atendido", "recusado"]: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status do pedido inválido. Valores permitidos: pendente, atendido, recusado.")
    return crud.atualizar_status_pedido_musica(db, pedido_db_obj=pedido_db, novo_status=status_update.status_pedido)

# --- Rota Raiz ---
@app.get("/", tags=["Geral"], summary="Endpoint Raiz da API")
async def root(): return {"message": "Bem-vindo ao PalcoApp API! O cérebro está funcionando!"}

# --- Rota de Itens (Exemplo) ---
@app.get("/items/{item_id}", tags=["Geral - Exemplo"], include_in_schema=False, summary="Exemplo de rota com parâmetro")
async def read_item(item_id: int, q: Optional[str] = None): return {"item_id": item_id, "q": q}