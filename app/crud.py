# app/crud.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func 
from typing import Optional, List
import datetime
# import logging 

from . import models, schemas
from .security import verificar_senha, obter_hash_da_senha

# logger = logging.getLogger(__name__)

# --- Funções CRUD para Músicos ---
def obter_musico_por_email(db: Session, email: str) -> Optional[models.Musico]:
    # # --- PRINTS DE DEPURAÇÃO COMENTADOS ---
    # print(f"    [CRUD.PY - obter_musico_por_email] Buscando músico com email: '{email}'")
    musico = db.query(models.Musico).filter(models.Musico.email == email).first()
    # if musico:
    #     print(f"    [CRUD.PY - obter_musico_por_email] Músico encontrado: ID={musico.id}, Email='{musico.email}'")
    # else:
    #     print(f"    [CRUD.PY - obter_musico_por_email] Músico com email '{email}' NÃO encontrado.")
    return musico

def atualizar_foto_perfil_musico(db: Session, musico_id: int, foto_url: str) -> Optional[models.Musico]:
    db_musico = obter_musico_por_id(db, musico_id=musico_id) 
    if db_musico:
        db_musico.foto_perfil_url = foto_url
        db.commit()
        db.refresh(db_musico)
        return db_musico
    return None

def obter_musico_por_id(db: Session, musico_id: int) -> Optional[models.Musico]:
    return db.query(models.Musico).options(
        joinedload(models.Musico.itens_repertorio),
        joinedload(models.Musico.shows),
        joinedload(models.Musico.pedidos_recebidos).joinedload(models.PedidoMusica.solicitante),
        joinedload(models.Musico.pedidos_recebidos).joinedload(models.PedidoMusica.item_repertorio_pedido)
    ).filter(models.Musico.id == musico_id).first()

def obter_musicos(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    search_term: Optional[str] = None,
    genero_filter: Optional[str] = None 
) -> List[models.Musico]:
    
    query = db.query(models.Musico).filter(models.Musico.is_active == True)

    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(models.Musico.nome_artistico.ilike(search_pattern))
        # print(f"CRUD obter_musicos: Aplicando filtro de busca por nome: '{search_term}'")

    if genero_filter: 
        genero_pattern = f"%{genero_filter}%" 
        query = query.filter(models.Musico.generos_musicais.ilike(genero_pattern))
        # print(f"CRUD obter_musicos: Aplicando filtro de gênero: '{genero_filter}'")
    
    musicos = query.options(
        joinedload(models.Musico.itens_repertorio), 
        joinedload(models.Musico.shows)             
    ).order_by(models.Musico.nome_artistico.asc()).offset(skip).limit(limit).all()
    
    # print(f"CRUD obter_musicos: Retornando {len(musicos)} músicos com os filtros aplicados.")
    return musicos

def criar_musico(db: Session, musico: schemas.MusicoCreate) -> models.Musico:
    senha_hasheada = obter_hash_da_senha(musico.password)
    db_musico = models.Musico(
        email=musico.email, nome_artistico=musico.nome_artistico,
        hashed_password=senha_hasheada, generos_musicais=musico.generos_musicais,
        descricao=musico.descricao, link_gorjeta=musico.link_gorjeta
    )
    db.add(db_musico)
    db.commit()
    db.refresh(db_musico)
    return db_musico

def autenticar_musico(db: Session, email: str, senha_texto_plano: str) -> Optional[models.Musico]:
    # # --- PRINTS DE DEPURAÇÃO COMENTADOS ---
    # print(f"  [CRUD.PY - autenticar_musico] Iniciando autenticação para email de MÚSICO: '{email}'")

    musico_no_banco = obter_musico_por_email(db, email=email) 
    
    if not musico_no_banco:
        return None
    
    # print(f"  [CRUD.PY - autenticar_musico] Senha HASHED armazenada para MÚSICO '{email}': '{musico_no_banco.hashed_password if hasattr(musico_no_banco, 'hashed_password') else 'N/A'}'")
    
    senha_correta = verificar_senha(senha_texto_plano, musico_no_banco.hashed_password)
    
    # print(f"  [CRUD.PY - autenticar_musico] Resultado da verificação de senha para MÚSICO '{email}' (senha_correta): {senha_correta}")
    # if not senha_correta:
    #     print(f"  [CRUD.PY - autenticar_musico] Verificação de senha FALHOU para o MÚSICO '{email}'.")
    # else:
    #     print(f"  [CRUD.PY - autenticar_musico] Verificação de senha BEM-SUCEDIDA para o MÚSICO '{email}'.")
        
    if not senha_correta:
        return None
    return musico_no_banco

def atualizar_musico(db: Session, musico_db_obj: models.Musico, musico_update_data: schemas.MusicoUpdate) -> models.Musico:
    update_data = musico_update_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(musico_db_obj, key):
            setattr(musico_db_obj, key, value)
    db.add(musico_db_obj)
    db.commit()
    db.refresh(musico_db_obj)
    return musico_db_obj

# --- Funções CRUD para Itens de Repertório ---
def obter_item_repertorio_por_id(db: Session, item_id: int) -> Optional[models.ItemRepertorio]:
    return db.query(models.ItemRepertorio).filter(models.ItemRepertorio.id == item_id).first()
    
def criar_item_repertorio_para_musico(db: Session, item: schemas.ItemRepertorioCreate, musico_id: int) -> models.ItemRepertorio:
    db_item = models.ItemRepertorio(**item.model_dump(), musico_id=musico_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def obter_itens_repertorio_do_musico(db: Session, musico_id: int, skip: int = 0, limit: int = 100) -> List[models.ItemRepertorio]:
    return db.query(models.ItemRepertorio).filter(models.ItemRepertorio.musico_id == musico_id).offset(skip).limit(limit).all()

def obter_item_repertorio_do_musico_por_id(db: Session, item_id: int, musico_id: int) -> Optional[models.ItemRepertorio]:
    return db.query(models.ItemRepertorio).filter(models.ItemRepertorio.id == item_id, models.ItemRepertorio.musico_id == musico_id).first()

def atualizar_item_repertorio_do_musico(
    db: Session, 
    item_id: int, 
    musico_id: int, 
    item_update: schemas.ItemRepertorioUpdate
) -> Optional[models.ItemRepertorio]:
    db_item = obter_item_repertorio_do_musico_por_id(db, item_id=item_id, musico_id=musico_id)
    if not db_item:
        return None
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def deletar_item_repertorio_do_musico(db: Session, item_id: int, musico_id: int) -> Optional[models.ItemRepertorio]:
    db_item = obter_item_repertorio_do_musico_por_id(db, item_id=item_id, musico_id=musico_id)
    if not db_item:
        return None
    db.delete(db_item)
    db.commit()
    return db_item 

# --- Funções CRUD para Shows ---
def criar_show_para_musico(db: Session, show: schemas.ShowCreate, musico_id: int) -> models.Show:
    show_data_dict = show.model_dump()
    if show_data_dict.get("link_evento") is not None:
        show_data_dict["link_evento"] = str(show_data_dict["link_evento"])
    db_show = models.Show(**show_data_dict, musico_id=musico_id)
    db.add(db_show)
    db.commit()
    db.refresh(db_show)
    return db_show

def obter_shows_do_musico(db: Session, musico_id: int, skip: int = 0, limit: int = 100) -> List[models.Show]:
    return db.query(models.Show).filter(models.Show.musico_id == musico_id).order_by(models.Show.data_hora_evento.asc()).offset(skip).limit(limit).all()

def obter_todos_os_shows(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    data_filtro: Optional[datetime.date] = None 
) -> List[models.Show]:
    query = db.query(models.Show).options(
        joinedload(models.Show.musico) 
    )
    if data_filtro:
        query = query.filter(func.date(models.Show.data_hora_evento) == data_filtro)
        # print(f"CRUD obter_todos_os_shows: Aplicando filtro de data_especifica: '{data_filtro}'")
    else:
        agora = datetime.datetime.now(datetime.timezone.utc)
        query = query.filter(models.Show.data_hora_evento >= agora)
        # print(f"CRUD obter_todos_os_shows: Listando shows futuros a partir de {agora}")
    query = query.order_by(models.Show.data_hora_evento.asc())
    shows = query.offset(skip).limit(limit).all()
    # print(f"CRUD obter_todos_os_shows: Retornando {len(shows)} shows com os filtros aplicados.")
    return shows

def obter_show_por_id(db: Session, show_id: int) -> Optional[models.Show]:
    show = db.query(models.Show).options(
        joinedload(models.Show.musico) 
    ).filter(models.Show.id == show_id).first()
    # if show:
    #     print(f"CRUD obter_show_por_id: Show ID {show_id} encontrado: {show.local_nome}, Músico: {show.musico.nome_artistico if show.musico else 'N/A'}")
    # else:
    #     print(f"CRUD obter_show_por_id: Show ID {show_id} NÃO encontrado.")
    return show

def obter_show_do_musico_por_id(db: Session, show_id: int, musico_id: int) -> Optional[models.Show]:
    return db.query(models.Show).filter(models.Show.id == show_id, models.Show.musico_id == musico_id).first()

def atualizar_show_do_musico(
    db: Session, 
    show_id: int, 
    musico_id: int, 
    show_update_data: schemas.ShowUpdate
) -> Optional[models.Show]:
    db_show = obter_show_do_musico_por_id(db, show_id=show_id, musico_id=musico_id)
    if not db_show:
        return None
    update_data = show_update_data.model_dump(exclude_unset=True)
    if "link_evento" in update_data and update_data["link_evento"] is not None:
        update_data["link_evento"] = str(update_data["link_evento"])
    for key, value in update_data.items():
        setattr(db_show, key, value)
    db.add(db_show)
    db.commit()
    db.refresh(db_show)
    return db_show

def deletar_show_do_musico(db: Session, show_id: int, musico_id: int) -> Optional[models.Show]:
    db_show = obter_show_do_musico_por_id(db, show_id=show_id, musico_id=musico_id)
    if not db_show:
        return None
    db.delete(db_show)
    db.commit()
    return db_show 

# --- Funções CRUD para UsuarioPublico (Fãs) ---
def obter_usuario_publico_por_email(db: Session, email: str) -> Optional[models.UsuarioPublico]:
    # # --- PRINTS DE DEPURAÇÃO COMENTADOS (E OS DE TESTE QUE ADICIONAMOS) ---
    # print(f"    [CRUD.PY - obter_usuario_publico_por_email] Buscando usuário (fã) com email (original): '{email}'")
    # total_usuarios = db.query(models.UsuarioPublico).count()
    # print(f"    [CRUD.PY - obter_usuario_publico_por_email] Total de usuários na tabela 'usuarios_publico': {total_usuarios}")
    # email_param = email.lower() 
    # print(f"    [CRUD.PY - obter_usuario_publico_por_email] Buscando com ILIKE e email normalizado para minúsculas: '{email_param}'")
    # usuario_ilike = db.query(models.UsuarioPublico).filter(func.lower(models.UsuarioPublico.email) == email_param).first()
    # if usuario_ilike:
    #     print(f"    [CRUD.PY - obter_usuario_publico_por_email] Usuário (fã) ENCONTRADO com ILIKE: ID={usuario_ilike.id}, Email='{usuario_ilike.email}'")
    # else:
    #     print(f"    [CRUD.PY - obter_usuario_publico_por_email] Usuário (fã) com email '{email}' NÃO encontrado mesmo com ILIKE.")
    
    usuario_original = db.query(models.UsuarioPublico).filter(models.UsuarioPublico.email == email).first()
    # if usuario_original:
    #     print(f"    [CRUD.PY - obter_usuario_publico_por_email] Resultado da busca ORIGINAL (==): ENCONTRADO - ID={usuario_original.id}, Email='{usuario_original.email}'")
    # else:
    #     print(f"    [CRUD.PY - obter_usuario_publico_por_email] Resultado da busca ORIGINAL (==): NÃO ENCONTRADO para email '{email}'")
    return usuario_original

def obter_usuario_publico_por_id(db: Session, usuario_id: int) -> Optional[models.UsuarioPublico]:
    return db.query(models.UsuarioPublico).options(
        joinedload(models.UsuarioPublico.musicos_favoritos).joinedload(models.Musico.itens_repertorio),
        joinedload(models.UsuarioPublico.musicos_favoritos).joinedload(models.Musico.shows),            
        joinedload(models.UsuarioPublico.pedidos_feitos).joinedload(models.PedidoMusica.musico_destinatario),
        joinedload(models.UsuarioPublico.pedidos_feitos).joinedload(models.PedidoMusica.item_repertorio_pedido)
    ).filter(models.UsuarioPublico.id == usuario_id).first()

def criar_usuario_publico(db: Session, usuario: schemas.UsuarioPublicoCreate) -> models.UsuarioPublico:
    senha_hasheada = obter_hash_da_senha(usuario.password)
    db_usuario = models.UsuarioPublico(
        email=usuario.email, 
        nome_completo=usuario.nome_completo, 
        hashed_password=senha_hasheada
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def autenticar_usuario_publico(db: Session, email: str, senha_texto_plano: str) -> Optional[models.UsuarioPublico]:
    # # --- PRINTS DE DEPURAÇÃO COMENTADOS ---
    # print(f"  [CRUD.PY - autenticar_usuario_publico] Iniciando autenticação para email de FÃ: '{email}'")

    usuario_no_banco = obter_usuario_publico_por_email(db, email=email) 
    
    if not usuario_no_banco:
        return None
    
    # print(f"  [CRUD.PY - autenticar_usuario_publico] Senha HASHED armazenada para FÃ '{email}': '{usuario_no_banco.hashed_password if hasattr(usuario_no_banco, 'hashed_password') else 'N/A'}'")
    
    senha_correta = verificar_senha(senha_texto_plano, usuario_no_banco.hashed_password)
    
    # print(f"  [CRUD.PY - autenticar_usuario_publico] Resultado da verificação de senha para FÃ '{email}' (senha_correta): {senha_correta}")
    # if not senha_correta:
    #     print(f"  [CRUD.PY - autenticar_usuario_publico] Verificação de senha FALHOU para o FÃ '{email}'.")
    # else:
    #     print(f"  [CRUD.PY - autenticar_usuario_publico] Verificação de senha BEM-SUCEDIDA para o FÃ '{email}'.")
        
    if not senha_correta:
        return None
    return usuario_no_banco

def atualizar_usuario_publico(
    db: Session, 
    usuario_db_obj: models.UsuarioPublico, 
    usuario_update_data: schemas.UsuarioPublicoUpdate
    ) -> models.UsuarioPublico:
    update_data = usuario_update_data.model_dump(exclude_unset=True) 
    
    # print(f"CRUD atualizar_usuario_publico: Dados para update: {update_data}")

    for key, value in update_data.items():
        if hasattr(usuario_db_obj, key):
            setattr(usuario_db_obj, key, value)
    
    db.add(usuario_db_obj)
    db.commit()
    db.refresh(usuario_db_obj)
    # print(f"CRUD atualizar_usuario_publico: Usuário ID {usuario_db_obj.id} atualizado. Novo nome: {usuario_db_obj.nome_completo}")
    return usuario_db_obj

# --- Funções CRUD para Favoritos ---
def verificar_se_musico_e_favorito(db: Session, usuario_id: int, musico_id: int) -> bool:
    usuario = db.query(models.UsuarioPublico).options(joinedload(models.UsuarioPublico.musicos_favoritos)).filter(models.UsuarioPublico.id == usuario_id).first()
    if usuario:
        for musico_fav in usuario.musicos_favoritos:
            if musico_fav.id == musico_id:
                return True
    return False

def adicionar_musico_aos_favoritos(db: Session, usuario: models.UsuarioPublico, musico: models.Musico) -> models.UsuarioPublico:
    if musico not in usuario.musicos_favoritos:
        usuario.musicos_favoritos.append(musico)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario

def remover_musico_dos_favoritos(db: Session, usuario: models.UsuarioPublico, musico: models.Musico) -> models.UsuarioPublico:
    if musico in usuario.musicos_favoritos:
        usuario.musicos_favoritos.remove(musico)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario

# --- Funções CRUD para Pedidos de Música ---
def criar_pedido_musica(
    db: Session, pedido_data: schemas.PedidoMusicaCreate, solicitante_id: int
) -> models.PedidoMusica:
    db_pedido = models.PedidoMusica(
        solicitante_id=solicitante_id,
        musico_id=pedido_data.musico_id,
        item_repertorio_id=pedido_data.item_repertorio_id,
        mensagem_opcional=pedido_data.mensagem_opcional
    )
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def obter_pedidos_para_musico(
    db: Session, musico_id: int, skip: int = 0, limit: int = 100
) -> List[models.PedidoMusica]:
    return (
        db.query(models.PedidoMusica)
        .filter(models.PedidoMusica.musico_id == musico_id)
        .options(
            joinedload(models.PedidoMusica.solicitante),
            joinedload(models.PedidoMusica.item_repertorio_pedido)
        )
        .order_by(models.PedidoMusica.data_hora_pedido.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def obter_pedidos_feitos_por_fan(
    db: Session, solicitante_id: int, skip: int = 0, limit: int = 100
) -> List[models.PedidoMusica]:
    return (
        db.query(models.PedidoMusica)
        .filter(models.PedidoMusica.solicitante_id == solicitante_id)
        .options( 
            joinedload(models.PedidoMusica.musico_destinatario),
            joinedload(models.PedidoMusica.item_repertorio_pedido)
        )
        .order_by(models.PedidoMusica.data_hora_pedido.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def obter_pedido_musica_por_id(
    db: Session, pedido_id: int, musico_id: Optional[int] = None # Tornando musico_id opcional
) -> Optional[models.PedidoMusica]:
    query = db.query(models.PedidoMusica).filter(models.PedidoMusica.id == pedido_id)
    if musico_id is not None: 
        query = query.filter(models.PedidoMusica.musico_id == musico_id)
    return query.first()


def atualizar_status_pedido_musica(
    db: Session, pedido_db_obj: models.PedidoMusica, novo_status: str
) -> models.PedidoMusica:
    pedido_db_obj.status_pedido = novo_status
    db.add(pedido_db_obj)
    db.commit()
    db.refresh(pedido_db_obj)
    return pedido_db_obj