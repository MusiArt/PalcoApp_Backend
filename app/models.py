# app/models.py
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from .database import Base
import datetime

# Tabela de associação para Favoritos (existente)
favoritos_table = Table(
    "usuario_musico_favoritos", Base.metadata,
    Column("usuario_publico_id", Integer, ForeignKey("usuarios_publico.id"), primary_key=True),
    Column("musico_id", Integer, ForeignKey("musicos.id"), primary_key=True),
)

class Musico(Base):
    __tablename__ = "musicos"
    id = Column(Integer, primary_key=True, index=True)
    nome_artistico = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    generos_musicais = Column(String, nullable=True)
    descricao = Column(String, nullable=True)
    link_gorjeta = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    foto_perfil_url = Column(String, nullable=True) # Armazenará o caminho/URL da foto
    
    itens_repertorio = relationship("ItemRepertorio", back_populates="musico_dono", cascade="all, delete-orphan")
    shows = relationship("Show", back_populates="musico", cascade="all, delete-orphan")
    favoritado_por = relationship("UsuarioPublico", secondary=favoritos_table, back_populates="musicos_favoritos")
    
    # NOVO RELACIONAMENTO: Pedidos recebidos por este músico
    pedidos_recebidos = relationship("PedidoMusica", back_populates="musico_destinatario", cascade="all, delete-orphan", foreign_keys="[PedidoMusica.musico_id]")


class ItemRepertorio(Base):
    __tablename__ = "itens_repertorio"
    id = Column(Integer, primary_key=True, index=True)
    nome_musica = Column(String, index=True)
    artista_original = Column(String, nullable=True)
    musico_id = Column(Integer, ForeignKey("musicos.id"))
    musico_dono = relationship("Musico", back_populates="itens_repertorio")
    
    # NOVO RELACIONAMENTO: Pedidos feitos para este item de repertório
    pedidos_desta_musica = relationship("PedidoMusica", back_populates="item_repertorio_pedido", cascade="all, delete-orphan")


class Show(Base):
    __tablename__ = "shows"
    id = Column(Integer, primary_key=True, index=True)
    data_hora_evento = Column(DateTime, nullable=False, index=True)
    local_nome = Column(String, nullable=False)
    local_endereco = Column(String, nullable=True)
    descricao_evento = Column(Text, nullable=True)
    link_evento = Column(String, nullable=True)
    data_hora_cadastro = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    musico_id = Column(Integer, ForeignKey("musicos.id"), nullable=False)
    musico = relationship("Musico", back_populates="shows")

class UsuarioPublico(Base):
    __tablename__ = "usuarios_publico"
    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    data_cadastro = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    musicos_favoritos = relationship("Musico", secondary=favoritos_table, back_populates="favoritado_por")
    
    # NOVO RELACIONAMENTO: Pedidos feitos por este usuário
    pedidos_feitos = relationship("PedidoMusica", back_populates="solicitante", cascade="all, delete-orphan", foreign_keys="[PedidoMusica.solicitante_id]")


# --- NOVO MODELO PedidoMusica ABAIXO ---
class PedidoMusica(Base):
    __tablename__ = "pedidos_musica"

    id = Column(Integer, primary_key=True, index=True)
    
    # Quem pediu? (Foreign Key para UsuarioPublico)
    solicitante_id = Column(Integer, ForeignKey("usuarios_publico.id"), nullable=False)
    solicitante = relationship("UsuarioPublico", back_populates="pedidos_feitos")

    # Para qual músico? (Foreign Key para Musico)
    musico_id = Column(Integer, ForeignKey("musicos.id"), nullable=False)
    musico_destinatario = relationship("Musico", back_populates="pedidos_recebidos")

    # Qual música? (Foreign Key para ItemRepertorio)
    item_repertorio_id = Column(Integer, ForeignKey("itens_repertorio.id"), nullable=False)
    item_repertorio_pedido = relationship("ItemRepertorio", back_populates="pedidos_desta_musica")
    
    # Informações do Pedido
    mensagem_opcional = Column(Text, nullable=True)
    data_hora_pedido = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), index=True)
    status_pedido = Column(String, default="pendente", index=True) # Ex: "pendente", "atendido", "recusado"