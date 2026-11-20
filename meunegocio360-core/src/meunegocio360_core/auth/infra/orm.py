"""Tabelas da feature auth e mapeamento imperativo das entidades de domínio.

As tabelas espelham as migrations ``0001`` e ``0002`` (RNF-BE-22, RNF-BE-23); elas servem ao
SQLAlchemy e ao ``alembic check``, nunca para criar o schema.
"""

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Uuid,
)
from sqlalchemy.types import TIMESTAMP

from meunegocio360_core.auth.domain.refresh_token import RefreshToken
from meunegocio360_core.auth.domain.usuario import Perfil, Usuario
from meunegocio360_core.shared.banco import mapeador, metadata


def _instante(nome: str, *, nullable: bool = False) -> Column:
    return Column(nome, TIMESTAMP(timezone=True), nullable=nullable)


tabela_usuario = Table(
    "usuario",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("nome", String(120), nullable=False),
    Column("email", String(160), nullable=False, unique=True),
    Column("senha_hash", String(100), nullable=False),
    Column(
        "perfil",
        Enum(
            Perfil,
            native_enum=False,
            create_constraint=False,
            length=20,
            values_callable=lambda enum: [membro.value for membro in enum],
        ),
        nullable=False,
    ),
    Column("ativo", Boolean, nullable=False, server_default="true"),
    Column("tentativas_falhas", Integer, nullable=False, server_default="0"),
    _instante("bloqueado_ate", nullable=True),
    _instante("ultimo_login_em", nullable=True),
    _instante("criado_em"),
    _instante("atualizado_em"),
    Column("versao", BigInteger, nullable=False),
    CheckConstraint(
        "perfil IN ('ADMIN', 'OPERADOR_COMERCIAL', 'OPERADOR_FINANCEIRO')", name="perfil_valido"
    ),
    CheckConstraint("tentativas_falhas >= 0", name="tentativas_nao_negativas"),
)

tabela_refresh_token = Table(
    "refresh_token",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("usuario_id", Uuid, ForeignKey("usuario.id"), nullable=False, index=True),
    Column("familia_id", Uuid, nullable=False, index=True),
    Column("token_hash", CHAR(64), nullable=False, unique=True),
    _instante("expira_em"),
    _instante("revogado_em", nullable=True),
    _instante("criado_em"),
    _instante("atualizado_em"),
    Column("versao", BigInteger, nullable=False),
)

_mapeado = False


def mapear() -> None:
    """Liga as classes de domínio às tabelas (idempotente)."""
    global _mapeado
    if _mapeado:
        return
    mapeador.map_imperatively(Usuario, tabela_usuario, version_id_col=tabela_usuario.c.versao)
    mapeador.map_imperatively(
        RefreshToken, tabela_refresh_token, version_id_col=tabela_refresh_token.c.versao
    )
    _mapeado = True
