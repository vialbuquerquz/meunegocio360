"""Criar tabela empresa (RF-BE-002, "Modelo de dados").

No máximo uma empresa ativa (RN-02) é garantida pelo índice único parcial
``uk_empresa_ativa_unica``; o CNPJ é único entre todas as empresas (RN-01). A tabela empresa é
a única de negócio sem ``empresa_id``: as próximas a referenciam (RNF-BE-26).

Revisão: 0004
Anterior: 0003

Migrations aplicadas NUNCA são editadas (RNF-BE-20): crie uma nova revisão.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    instante = sa.TIMESTAMP(timezone=True)
    op.create_table(
        "empresa",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("razao_social", sa.String(150), nullable=False),
        sa.Column("nome_fantasia", sa.String(150), nullable=True),
        sa.Column("cnpj", sa.CHAR(14), nullable=False),
        sa.Column("email", sa.String(160), nullable=True),
        sa.Column("telefone", sa.String(11), nullable=True),
        sa.Column(
            "fuso_horario", sa.String(50), nullable=False, server_default="America/Sao_Paulo"
        ),
        sa.Column("moeda", sa.CHAR(3), nullable=False, server_default="BRL"),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", instante, nullable=False),
        sa.Column("atualizado_em", instante, nullable=False),
        sa.Column("versao", sa.BigInteger(), nullable=False),
        # op.f(): nomes definitivos, sem a convenção do metadata (que duplicaria o prefixo).
        sa.PrimaryKeyConstraint("id", name=op.f("pk_empresa")),
        sa.UniqueConstraint("cnpj", name=op.f("uk_empresa_cnpj")),
        sa.CheckConstraint("cnpj ~ '^[0-9]{14}$'", name=op.f("ck_empresa_cnpj_digitos")),
        sa.CheckConstraint("telefone ~ '^[0-9]{10,11}$'", name=op.f("ck_empresa_telefone_digitos")),
    )
    op.create_index(
        op.f("uk_empresa_ativa_unica"),
        "empresa",
        ["ativa"],
        unique=True,
        postgresql_where=sa.text("ativa"),
    )


def downgrade() -> None:
    op.drop_table("empresa")
