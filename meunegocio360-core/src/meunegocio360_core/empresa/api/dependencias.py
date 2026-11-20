"""Montagem dos casos de uso por requisição, com injeção por construtor (RNF-BE-03)."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from meunegocio360_core.empresa.application.casos_de_uso import (
    AlterarSituacaoEmpresa,
    AtualizarEmpresa,
    CadastrarEmpresa,
    ObterEmpresaAtiva,
)
from meunegocio360_core.empresa.application.comum import FabricaDeUnidadeDeTrabalho
from meunegocio360_core.empresa.application.empresa_ativa import EmpresaAtiva
from meunegocio360_core.shared.documentacao import exemplo_de_erro
from meunegocio360_core.shared.relogio import Relogio


@dataclass(frozen=True)
class ContextoEmpresa:
    nova_unidade_de_trabalho: FabricaDeUnidadeDeTrabalho
    relogio: Relogio
    empresa_ativa: EmpresaAtiva


def _contexto(request: Request) -> ContextoEmpresa:
    return request.app.state.empresa


Contexto = Annotated[ContextoEmpresa, Depends(_contexto)]


def obter_empresa_ativa(ctx: Contexto) -> ObterEmpresaAtiva:
    return ObterEmpresaAtiva(ctx.nova_unidade_de_trabalho)


def cadastrar_empresa(ctx: Contexto) -> CadastrarEmpresa:
    return CadastrarEmpresa(ctx.nova_unidade_de_trabalho, ctx.relogio)


def atualizar_empresa(ctx: Contexto) -> AtualizarEmpresa:
    return AtualizarEmpresa(ctx.nova_unidade_de_trabalho, ctx.relogio)


def alterar_situacao_empresa(ctx: Contexto) -> AlterarSituacaoEmpresa:
    return AlterarSituacaoEmpresa(ctx.nova_unidade_de_trabalho, ctx.relogio)


# ----------------------------------------------------------------- uso por outras features


def empresa_ativa(ctx: Contexto) -> EmpresaAtiva:
    """Dependência para as rotas de RF-BE-003 em diante: entrega o componente ``EmpresaAtiva``,
    que resolve o ``empresa_id`` no servidor (RNF-096)."""
    return ctx.empresa_ativa


# Entrada de ``responses`` para as rotas que exigem empresa ativa (documentação no OpenAPI).
RESPOSTA_EMPRESA_NAO_ATIVA = {
    422: exemplo_de_erro(422, "COMPANY_NOT_ACTIVE", "Não há empresa ativa (RNF-096)")
}
