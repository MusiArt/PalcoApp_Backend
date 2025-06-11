# app/schemas.py
from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict
from typing import Optional, List
import datetime

# --- Esquemas "Slim" (já existentes, MusicoSlim é importante aqui) ---
class MusicoSlim(BaseModel):
    id: int
    nome_artistico: str
    foto_perfil_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ... (outros schemas ItemRepertorioBase, ItemRepertorioCreate, etc. permanecem os mesmos) ...
class ItemRepertorioBase(BaseModel):
    nome_musica: str
    artista_original: Optional[str] = None
class ItemRepertorioCreate(ItemRepertorioBase): pass
class ItemRepertorioUpdate(BaseModel):
    nome_musica: Optional[str] = None
    artista_original: Optional[str] = None
class ItemRepertorio(ItemRepertorioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Esquemas para Shows ---
class ShowBase(BaseModel):
    data_hora_evento: datetime.datetime
    local_nome: str
    local_endereco: Optional[str] = None
    descricao_evento: Optional[str] = None
    link_evento: Optional[HttpUrl] = None

class ShowCreate(ShowBase): pass

class ShowUpdate(BaseModel):
    data_hora_evento: Optional[datetime.datetime] = None
    local_nome: Optional[str] = None
    local_endereco: Optional[str] = None
    descricao_evento: Optional[str] = None
    link_evento: Optional[HttpUrl] = None

# ***** ALTERAÇÃO AQUI NO SCHEMAS.SHOW *****
class Show(ShowBase): # Este é o schema que será usado como response_model para listas de shows
    id: int
    # musico_id: int # Ainda pode ser mantido se quiser o ID explícito, mas o objeto musico já o terá.
                   # Se o frontend já espera musico_id, mantenha.
                   # Para evitar redundância, podemos remover se o objeto musico for sempre incluído.
                   # Por ora, vou manter, mas o frontend usará o musico.nome_artistico.
    data_hora_cadastro: datetime.datetime
    musico: MusicoSlim # <<< NOVO CAMPO PARA INCLUIR DETALHES DO MÚSICO

    model_config = ConfigDict(from_attributes=True)
# ***** FIM DA ALTERAÇÃO *****


# ... (UsuarioPublicoSlim, ItemRepertorioSlim, PedidoMusica, Musico, UsuarioPublico, Token, TokenData - permanecem os mesmos) ...
class UsuarioPublicoSlim(BaseModel):
    id: int
    nome_completo: Optional[str] = None
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)
    
class ItemRepertorioSlim(BaseModel):
    id: int
    nome_musica: str
    artista_original: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PedidoMusicaBase(BaseModel):
    mensagem_opcional: Optional[str] = None
class PedidoMusicaCreate(PedidoMusicaBase):
    item_repertorio_id: int
    musico_id: int
class PedidoMusicaUpdateStatus(BaseModel):
    status_pedido: str
class PedidoMusica(PedidoMusicaBase):
    id: int
    data_hora_pedido: datetime.datetime
    status_pedido: str
    solicitante: UsuarioPublicoSlim
    musico_destinatario: MusicoSlim
    item_repertorio_pedido: ItemRepertorioSlim
    model_config = ConfigDict(from_attributes=True)

class MusicoBase(BaseModel):
    id: int
    nome_artistico: str
    generos_musicais: Optional[str] = None
    descricao: Optional[str] = None
    link_gorjeta: Optional[str] = None
    foto_perfil_url: Optional[str] = None
    itens_repertorio: List[ItemRepertorio] = []
    shows: List[Show] = [] # Esta lista de shows agora usará o schema Show modificado
    pedidos_recebidos: List[PedidoMusica] = []
    model_config = ConfigDict(from_attributes=True)

class MusicoCreate(BaseModel):
    nome_artistico: str; email: EmailStr; password: str = Field(..., min_length=6)
    generos_musicais: Optional[str] = None; descricao: Optional[str] = None; link_gorjeta: Optional[str] = None

class MusicoUpdate(BaseModel):
    nome_artistico: Optional[str] = None; generos_musicais: Optional[str] = None
    descricao: Optional[str] = None; link_gorjeta: Optional[str] = None

class Musico(MusicoBase): # Este schema também se beneficiará do Show modificado se for retornado em /musicos/me/
    email: EmailStr
    is_active: bool

class MusicoPublicProfile(MusicoBase): # E este também para /musicos/ e /musicos/{id}
    pass

class UsuarioPublicoBase(BaseModel):
    email: EmailStr
    nome_completo: Optional[str] = None
class UsuarioPublicoCreate(UsuarioPublicoBase):
    password: str = Field(..., min_length=6)
class UsuarioPublicoUpdate(BaseModel):
    nome_completo: Optional[str] = None
class UsuarioPublico(UsuarioPublicoBase):
    id: int
    is_active: bool
    data_cadastro: datetime.datetime
    musicos_favoritos: List[MusicoPublicProfile] = []
    pedidos_feitos: List[PedidoMusica] = []
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str; token_type: str; user_id: int; email: EmailStr; role: str; nome_exibicao: str
class TokenData(BaseModel):
    email: Optional[EmailStr] = None; user_id: Optional[int] = None; role: Optional[str] = None