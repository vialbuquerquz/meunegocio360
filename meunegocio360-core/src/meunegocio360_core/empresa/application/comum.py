"""Tipos compartilhados pelos casos de uso da empresa."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self

from meunegocio360_core.empresa.domain.empresa import Empresa
from meunegocio360_core.empresa.domain.portas import RepositorioDeEmpresas


class UnidadeDeTrabalho(Protocol):
    """Fronteira transacional (RNF-BE-04): sem ``commit()``, tudo é desfeito ao sair do ``with``.

    O ``commit()`` traduz violações do banco para erros de negócio (RNF-BE-15).
    """

    empresas: RepositorioDeEmpresas

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...


FabricaDeUnidadeDeTrabalho = Callable[[], UnidadeDeTrabalho]


@dataclass(frozen=True)
class EmpresaResumo:
    """O que a API devolve; a entidade nunca sai da camada de aplicação (RNF-BE-02)."""

    id: uuid.UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str
    email: str | None
    telefone: str | None
    fuso_horario: str
    moeda: str
    ativa: bool
    criado_em: datetime
    atualizado_em: datetime
    versao: int

    @classmethod
    def de(cls, empresa: Empresa) -> "EmpresaResumo":
        return cls(
            id=empresa.id,
            razao_social=empresa.razao_social,
            nome_fantasia=empresa.nome_fantasia,
            cnpj=empresa.cnpj,
            email=empresa.email,
            telefone=empresa.telefone,
            fuso_horario=empresa.fuso_horario,
            moeda=empresa.moeda,
            ativa=empresa.ativa,
            criado_em=empresa.criado_em,
            atualizado_em=empresa.atualizado_em,
            versao=empresa.versao,
        )
