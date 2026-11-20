"""Repositório SQLAlchemy e unidade de trabalho da feature empresa."""

import uuid
from types import TracebackType
from typing import Self

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from meunegocio360_core.empresa.domain.empresa import Empresa
from meunegocio360_core.empresa.domain.erros import CnpjDuplicadoError, EmpresaJaAtivaError
from meunegocio360_core.empresa.infra.orm import UK_ATIVA_UNICA, UK_CNPJ, tabela_empresa
from meunegocio360_core.shared.banco import FabricaDeSessoes
from meunegocio360_core.shared.dominio import VersaoDesatualizadaError

# Violações de unicidade traduzidas para o erro de negócio correspondente (RNF-BE-15).
_ERRO_POR_RESTRICAO = {UK_CNPJ: CnpjDuplicadoError, UK_ATIVA_UNICA: EmpresaJaAtivaError}


class RepositorioSqlDeEmpresas:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def buscar_ativa(self) -> Empresa | None:
        consulta = select(Empresa).where(tabela_empresa.c.ativa.is_(True))
        return self._sessao.scalars(consulta).one_or_none()

    def buscar_por_id_para_atualizacao(self, empresa_id: uuid.UUID) -> Empresa | None:
        consulta = select(Empresa).where(tabela_empresa.c.id == empresa_id).with_for_update()
        return self._sessao.scalars(consulta).one_or_none()

    def existe_cnpj(self, cnpj: str, *, exceto_id: uuid.UUID | None = None) -> bool:
        criterio = tabela_empresa.c.cnpj == cnpj
        if exceto_id is not None:
            criterio = criterio & (tabela_empresa.c.id != exceto_id)
        return bool(self._sessao.scalar(select(exists().where(criterio))))

    def existe_outra_ativa(self, exceto_id: uuid.UUID) -> bool:
        t = tabela_empresa
        return bool(self._sessao.scalar(select(exists().where(t.c.ativa, t.c.id != exceto_id))))

    def adicionar(self, empresa: Empresa) -> None:
        self._sessao.add(empresa)


class UnidadeDeTrabalhoSql:
    """Uma sessão (e transação) por caso de uso; sem commit explícito, tudo é desfeito."""

    empresas: RepositorioSqlDeEmpresas

    def __init__(self, fabrica_de_sessoes: FabricaDeSessoes) -> None:
        self._fabrica = fabrica_de_sessoes

    def __enter__(self) -> Self:
        self._sessao = self._fabrica()
        self.empresas = RepositorioSqlDeEmpresas(self._sessao)
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        self._sessao.rollback()
        self._sessao.close()

    def commit(self) -> None:
        """Confirma a transação. Corridas que só o banco detecta viram erros de negócio, e
        nunca um 500: duas alterações sobre a mesma versão (``VERSION_CONFLICT``) ou duas
        requisições que tentam o mesmo CNPJ ou a segunda empresa ativa ao mesmo tempo."""
        try:
            self._sessao.commit()
        except StaleDataError:
            raise VersaoDesatualizadaError from None
        except IntegrityError as erro:
            restricao = getattr(getattr(erro.orig, "diag", None), "constraint_name", None)
            if restricao in _ERRO_POR_RESTRICAO:
                raise _ERRO_POR_RESTRICAO[restricao] from None
            raise
