"""Erros de negócio da empresa. A tradução para HTTP está em ``empresa/api/problemas.py``."""

from meunegocio360_core.shared.dominio import ErroDeNegocio


class EmpresaNaoCadastradaError(ErroDeNegocio):
    """Consulta sem empresa ativa (``404 COMPANY_NOT_REGISTERED``): inicia o primeiro cadastro."""


class EmpresaNaoEncontradaError(ErroDeNegocio):
    """Nenhuma empresa com o ``id`` informado em ``PUT``/``PATCH``."""


class CnpjDuplicadoError(ErroDeNegocio):
    """RN-01: CNPJ já usado por outra empresa, ativa ou inativa."""


class EmpresaJaAtivaError(ErroDeNegocio):
    """RN-02: já existe uma empresa ativa (cadastro ou reativação)."""


class EmpresaNaoAtivaError(ErroDeNegocio):
    """RN-04 e RNF-096: operação de negócio sem empresa ativa (``422 COMPANY_NOT_ACTIVE``)."""
