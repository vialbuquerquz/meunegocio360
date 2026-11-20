"""Tradução dos erros de negócio da empresa para problem+json (RF-BE-002, tabela "Erros")."""

from meunegocio360_core.empresa.domain.erros import (
    CnpjDuplicadoError,
    EmpresaJaAtivaError,
    EmpresaNaoAtivaError,
    EmpresaNaoCadastradaError,
    EmpresaNaoEncontradaError,
)
from meunegocio360_core.shared.erros import Problema, registrar_traducao


def registrar_traducoes() -> None:
    registrar_traducao(
        EmpresaNaoCadastradaError,
        lambda _: Problema(
            404,
            "COMPANY_NOT_REGISTERED",
            "Empresa não cadastrada",
            "Não existe empresa ativa. Cadastre a empresa para começar.",
            "empresa-nao-cadastrada",
        ),
    )
    registrar_traducao(
        EmpresaNaoEncontradaError,
        lambda _: Problema(
            404,
            "NOT_FOUND",
            "Recurso não encontrado",
            "Empresa não encontrada.",
            "nao-encontrado",
        ),
    )
    registrar_traducao(
        CnpjDuplicadoError,
        lambda _: Problema(
            409,
            "COMPANY_CNPJ_DUPLICATE",
            "CNPJ já cadastrado",
            "Já existe uma empresa cadastrada com este CNPJ.",
            "cnpj-duplicado",
        ),
    )
    registrar_traducao(
        EmpresaJaAtivaError,
        lambda _: Problema(
            409,
            "COMPANY_ALREADY_ACTIVE",
            "Já existe empresa ativa",
            "Só pode existir uma empresa ativa. Inative a empresa atual antes.",
            "empresa-ja-ativa",
        ),
    )
    registrar_traducao(
        EmpresaNaoAtivaError,
        lambda _: Problema(
            422,
            "COMPANY_NOT_ACTIVE",
            "Empresa não ativa",
            "Não há empresa ativa. Cadastre ou reative a empresa antes desta operação.",
            "empresa-nao-ativa",
        ),
    )
