"""Entidade Usuario e as regras de autenticação que dependem só do seu estado (RF-BE-001)."""

import math
import uuid
from datetime import datetime, timedelta

# Os perfis são compartilhados pela autorização de todas as features (RF-BE-002, RN-07).
from meunegocio360_core.shared.dominio import Perfil

__all__ = ["Perfil", "Usuario"]


class Usuario:
    """Classe de domínio pura; o mapeamento para a tabela ``usuario`` fica em ``infra``."""

    # Atribuídos pelo mapeamento (``versao`` é o controle otimista, RNF-BE-22).
    versao: int

    def __init__(
        self,
        *,
        id: uuid.UUID,
        nome: str,
        email: str,
        senha_hash: str,
        perfil: Perfil,
        criado_em: datetime,
        ativo: bool = True,
    ) -> None:
        self.id = id
        self.nome = nome
        self.email = Usuario.normalizar_email(email)
        self.senha_hash = senha_hash
        self.perfil = perfil
        self.ativo = ativo
        self.tentativas_falhas = 0
        self.bloqueado_ate: datetime | None = None
        self.ultimo_login_em: datetime | None = None
        self.criado_em = criado_em
        self.atualizado_em = criado_em

    @staticmethod
    def normalizar_email(email: str) -> str:
        """RN-01: e-mail comparado sem diferenciar maiúsculas e armazenado em minúsculas."""
        return email.strip().lower()

    def esta_bloqueado(self, agora: datetime) -> bool:
        return self.bloqueado_ate is not None and self.bloqueado_ate > agora

    def segundos_ate_desbloqueio(self, agora: datetime) -> int:
        if self.bloqueado_ate is None or self.bloqueado_ate <= agora:
            return 0
        return math.ceil((self.bloqueado_ate - agora).total_seconds())

    def pode_manter_sessao(self, agora: datetime) -> bool:
        """RN-02 e RN-13: só usuários ativos e não bloqueados autenticam ou renovam sessão."""
        return self.ativo and not self.esta_bloqueado(agora)

    def registrar_falha_de_login(
        self, agora: datetime, *, max_tentativas: int, duracao_bloqueio: timedelta
    ) -> bool:
        """RN-04: conta falhas consecutivas e bloqueia ao atingir o limite.

        Devolve ``True`` quando esta falha causou o bloqueio. O contador volta a zero no
        bloqueio, para que, passado o período, o usuário tenha novamente todas as tentativas.
        """
        self.tentativas_falhas += 1
        self.atualizado_em = agora
        if self.tentativas_falhas < max_tentativas:
            return False
        self.bloqueado_ate = agora + duracao_bloqueio
        self.tentativas_falhas = 0
        return True

    def registrar_login(self, agora: datetime) -> None:
        """RN-04 e RN-12: login com sucesso zera o contador e registra ``ultimo_login_em``."""
        self.tentativas_falhas = 0
        self.bloqueado_ate = None
        self.ultimo_login_em = agora
        self.atualizado_em = agora

    def __repr__(self) -> str:  # nunca expor senha_hash nem e-mail completo
        return f"Usuario(id={self.id}, perfil={self.perfil}, ativo={self.ativo})"
