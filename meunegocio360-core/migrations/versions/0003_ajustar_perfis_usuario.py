"""Ajustar perfis de usuário (RF-BE-002, RN-07).

O perfil USUARIO deixa de existir: quem o tinha passa a OPERADOR_COMERCIAL. Os perfis válidos
são ADMIN, OPERADOR_COMERCIAL e OPERADOR_FINANCEIRO.

Revisão: 0003
Anterior: 0002

Migrations aplicadas NUNCA são editadas (RNF-BE-20): crie uma nova revisão.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A migration 0001 passou o nome já com o prefixo, e a convenção de nomes do metadata
# (``ck_%(table_name)s_%(constraint_name)s``) o acrescentou de novo: no banco, a restrição se
# chama ``ck_usuario_ck_usuario_perfil_valido``. ``op.f()`` marca o nome como definitivo
# (sem aplicar a convenção): remove-se o nome real e recria-se com o nome correto, igual ao
# esperado pelo ORM (``auth/infra/orm.py``).
RESTRICAO_ANTIGA = op.f("ck_usuario_ck_usuario_perfil_valido")
RESTRICAO = op.f("ck_usuario_perfil_valido")


def upgrade() -> None:
    op.drop_constraint(RESTRICAO_ANTIGA, "usuario", type_="check")
    # versao e atualizado_em acompanham a alteração (controle otimista, RNF-BE-22).
    op.execute(
        "UPDATE usuario SET perfil = 'OPERADOR_COMERCIAL', versao = versao + 1, "
        "atualizado_em = now() WHERE perfil = 'USUARIO'"
    )
    op.create_check_constraint(
        RESTRICAO, "usuario", "perfil IN ('ADMIN', 'OPERADOR_COMERCIAL', 'OPERADOR_FINANCEIRO')"
    )


def downgrade() -> None:
    # Volta ao modelo de dois perfis: os operadores (comercial e financeiro) viram USUARIO.
    op.drop_constraint(RESTRICAO, "usuario", type_="check")
    op.execute(
        "UPDATE usuario SET perfil = 'USUARIO', versao = versao + 1, atualizado_em = now() "
        "WHERE perfil IN ('OPERADOR_COMERCIAL', 'OPERADOR_FINANCEIRO')"
    )
    op.create_check_constraint(RESTRICAO_ANTIGA, "usuario", "perfil IN ('ADMIN', 'USUARIO')")
