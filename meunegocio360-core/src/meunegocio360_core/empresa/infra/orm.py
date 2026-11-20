"""Tabela ``empresa`` e mapeamento imperativo da entidade de domínio.

A tabela espelha a migration ``0004`` (RNF-BE-22, RNF-BE-23); ela serve ao SQLAlchemy e ao
``alembic check``, nunca para criar o schema.
"""

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Index,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.types import TIMESTAMP

from meunegocio360_core.empresa.domain.empresa import FUSO_HORARIO_PADRAO, MOEDA_PADRAO, Empresa
from meunegocio360_core.shared.banco import mapeador, metadata

# Nomes definidos pelo RF-BE-002 ("Modelo de dados").
UK_CNPJ = "uk_empresa_cnpj"
UK_ATIVA_UNICA = "uk_empresa_ativa_unica"

tabela_empresa = Table(
    "empresa",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("razao_social", String(150), nullable=False),
    Column("nome_fantasia", String(150), nullable=True),
    Column("cnpj", CHAR(14), nullable=False),
    Column("email", String(160), nullable=True),
    Column("telefone", String(11), nullable=True),
    Column("fuso_horario", String(50), nullable=False, server_default=FUSO_HORARIO_PADRAO),
    Column("moeda", CHAR(3), nullable=False, server_default=MOEDA_PADRAO),
    Column("ativa", Boolean, nullable=False, server_default=text("true")),
    Column("criado_em", TIMESTAMP(timezone=True), nullable=False),
    Column("atualizado_em", TIMESTAMP(timezone=True), nullable=False),
    Column("versao", BigInteger, nullable=False),
    UniqueConstraint("cnpj", name=UK_CNPJ),
    CheckConstraint("cnpj ~ '^[0-9]{14}$'", name="cnpj_digitos"),
    CheckConstraint("telefone ~ '^[0-9]{10,11}$'", name="telefone_digitos"),
    # RN-02 no banco: índice único parcial, só uma linha pode ter ativa = true.
    Index(UK_ATIVA_UNICA, "ativa", unique=True, postgresql_where=text("ativa")),
)

_mapeado = False


def _proxima_versao(atual: int | None) -> int:
    """A versão começa em 0 no cadastro e soma 1 a cada alteração (contrato do RF-BE-002)."""
    return 0 if atual is None else atual + 1


def mapear() -> None:
    """Liga a classe de domínio à tabela (idempotente)."""
    global _mapeado
    if _mapeado:
        return
    mapeador.map_imperatively(
        Empresa,
        tabela_empresa,
        version_id_col=tabela_empresa.c.versao,
        version_id_generator=_proxima_versao,
    )
    _mapeado = True
