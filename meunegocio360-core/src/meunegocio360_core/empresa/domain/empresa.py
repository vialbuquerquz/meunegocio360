"""Entidade Empresa e as regras que dependem só do seu estado (RF-BE-002)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from meunegocio360_core.shared.dominio import VersaoDesatualizadaError

FUSO_HORARIO_PADRAO = "America/Sao_Paulo"
MOEDA_PADRAO = "BRL"


@dataclass(frozen=True)
class DadosDaEmpresa:
    """Campos editáveis, já validados e normalizados pela camada ``api`` (RN-01, RN-05, RN-06)."""

    razao_social: str
    cnpj: str
    nome_fantasia: str | None = None
    email: str | None = None
    telefone: str | None = None
    fuso_horario: str = FUSO_HORARIO_PADRAO
    moeda: str = MOEDA_PADRAO


class Empresa:
    """Classe de domínio pura; o mapeamento para a tabela ``empresa`` fica em ``infra``."""

    # Atribuída pelo mapeamento (controle otimista, RNF-BE-22): 0 no cadastro.
    versao: int

    def __init__(self, *, id: uuid.UUID, dados: DadosDaEmpresa, criado_em: datetime) -> None:
        self.id = id
        self._aplicar(dados)
        self.ativa = True
        self.criado_em = criado_em
        self.atualizado_em = criado_em

    @classmethod
    def cadastrar(cls, dados: DadosDaEmpresa, agora: datetime) -> "Empresa":
        """A empresa já nasce ativa (contrato do ``POST /empresa``)."""
        return cls(id=uuid.uuid4(), dados=dados, criado_em=agora)

    def conferir_versao(self, versao: int) -> None:
        """RN-06 e RNF-BE-28: a alteração só vale sobre a versão que o cliente leu."""
        if versao != self.versao:
            raise VersaoDesatualizadaError

    def atualizar(self, dados: DadosDaEmpresa, agora: datetime) -> None:
        self._aplicar(dados)
        self.atualizado_em = agora

    def inativar(self, agora: datetime) -> None:
        """RN-04: a empresa é inativada, nunca excluída."""
        self.ativa = False
        self.atualizado_em = agora

    def reativar(self, agora: datetime) -> None:
        """Quem chama garante que não há outra ativa (RN-02); o banco também garante."""
        self.ativa = True
        self.atualizado_em = agora

    def _aplicar(self, dados: DadosDaEmpresa) -> None:
        self.razao_social = dados.razao_social
        self.nome_fantasia = dados.nome_fantasia
        self.cnpj = dados.cnpj
        self.email = dados.email
        self.telefone = dados.telefone
        self.fuso_horario = dados.fuso_horario
        self.moeda = dados.moeda

    def __repr__(self) -> str:
        return f"Empresa(id={self.id}, ativa={self.ativa})"
