from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine # Adicionado create_engine
from alembic import context

# Import sys e os para manipular o Python path e encontrar seus módulos
import sys
import os

# --- Configuração para encontrar seus módulos da aplicação ---
# Este bloco adiciona o diretório raiz do seu projeto ao sys.path
# para que o Alembic possa encontrar 'app.models' e 'app.database'.
# Ele assume que o script 'env.py' está em 'PALCOAPP_CEREBRO/alembic/env.py'
# e seu aplicativo está em 'PALCOAPP_CEREBRO/app/'
# current_dir = os.path.dirname(os.path.abspath(__file__)) # Diretório de env.py
# project_root = os.path.dirname(current_dir) # Diretório 'alembic'
# project_root_for_app = os.path.dirname(project_root) # Raiz do projeto PALCOAPP_CEREBRO
# app_dir = os.path.join(project_root_for_app, "app") # Caminho para a pasta 'app'

# Alternativa mais simples se alembic.ini está na raiz do projeto
# e o comando alembic é executado da raiz do projeto:
# Neste caso, o diretório de trabalho atual já deve permitir importar 'app'
# Se não funcionar, a abordagem com sys.path.append abaixo é mais robusta.

# Adiciona o diretório 'app' que está um nível acima da pasta 'alembic'
# (ou seja, na raiz do projeto PALCOAPP_CEREBRO) ao path do Python.
# Isso permite que 'from app.models import Base' funcione.
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
# Ou, se você roda os comandos alembic da pasta PALCOAPP_CEREBRO,
# e 'app' é uma subpasta direta, você pode não precisar modificar o sys.path aqui,
# mas é uma boa prática para garantir que os módulos sejam encontrados.
# Se os imports abaixo falharem, experimente a outra forma de adicionar ao sys.path comentada acima.

try:
    from app.models import Base  # Importa Base de app.models
    from app.database import DATABASE_URL # Importa DATABASE_URL de app.database
except ImportError as e:
    print(f"Erro ao importar módulos da aplicação em env.py: {e}")
    print(f"Verifique se os caminhos de import e a estrutura do projeto estão corretos.")
    print(f"sys.path atual: {sys.path}")
    # Se você tiver um arquivo de configuração separado para DATABASE_URL, ex: app.config
    # from app.config import settings
    # DATABASE_URL = settings.DATABASE_URL # Exemplo
    # E se Base estiver em app.database:
    # from app.database import Base
    raise e # Re-levanta a exceção para parar a execução se os imports falharem

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Usa a DATABASE_URL importada do seu projeto
    url = DATABASE_URL 
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Adicionado para PostgreSQL se houver schemas diferentes do padrão (ex: 'public')
        # include_schemas=True, 
        # version_table_schema='public', # Especifique o schema da tabela de versão do alembic
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Tenta pegar a URL da seção principal do alembic.ini, mas sobrescreve com a sua DATABASE_URL
    # Isso garante que usemos a mesma URL de conexão que a aplicação usa.
    
    # Cria um dicionário de configuração para engine_from_config
    # É importante que a chave 'sqlalchemy.url' esteja presente.
    configuration = config.get_section(config.config_ini_section)
    if configuration is None: # Fallback se a seção não existir no .ini
        configuration = {}
    configuration["sqlalchemy.url"] = DATABASE_URL # Define/Sobrescreve a URL

    connectable = engine_from_config(
        configuration, # Usa o dicionário de configuração
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    # Alternativamente, se engine_from_config der problemas ou para mais controle:
    # from sqlalchemy import create_engine
    # connectable = create_engine(DATABASE_URL)


    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # Adicionado para PostgreSQL (opcional, mas bom para autogenerate com schemas)
            # include_schemas=True,
            # version_table_schema='public', 
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()