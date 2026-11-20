"""Interfaces que os casos de uso esperam; ``infra`` as implementa (RNF-010)."""

import uuid
from typing import Protocol

from meunegocio360_core.empresa.domain.empresa import Empresa


class RepositorioDeEmpresas(Protocol):
    def buscar_ativa(self) -> Empresa | None: ...

    def buscar_por_id_para_atualizacao(self, empresa_id: uuid.UUID) -> Empresa | None:
        """Busca e bloqueia a linha (``FOR UPDATE``) durante a alteração."""
        ...

    def existe_cnpj(self, cnpj: str, *, exceto_id: uuid.UUID | None = None) -> bool: ...

    def existe_outra_ativa(self, exceto_id: uuid.UUID) -> bool: ...

    def adicionar(self, empresa: Empresa) -> None: ...
