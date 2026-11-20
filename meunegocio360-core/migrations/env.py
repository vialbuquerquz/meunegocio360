"""Ambiente do Alembic: conecta com as mesmas variáveis da aplicação."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Os módulos orm registram as tabelas no metadata (usado pelo ``alembic check``).
import meunegocio360_core.auth.infra.orm
import meunegocio360_core.empresa.infra.orm  # noqa: F401
from meunegocio360_core.shared.banco import metadata
from meunegocio360_core.shared.config import carregar_configuracao_banco

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

target_metadata = metadata


def executar_offline() -> None:
    url = carregar_configuracao_banco().url_sqlalchemy
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    engine = create_engine(carregar_configuracao_banco().url_sqlalchemy)
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
