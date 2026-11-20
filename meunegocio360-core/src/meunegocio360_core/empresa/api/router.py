"""Endpoints da empresa (RF-BE-002, "Contrato da API" e "Matriz de autorização").

Routers finos (RNF-BE-01): recebem o DTO, chamam um caso de uso e devolvem o DTO. A matriz de
perfis é aplicada aqui, em cada rota (RNF-BE-47); os erros viram problem+json no tratador único.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from meunegocio360_core.empresa.api.dependencias import (
    alterar_situacao_empresa,
    atualizar_empresa,
    cadastrar_empresa,
    obter_empresa_ativa,
)
from meunegocio360_core.empresa.api.schemas import (
    EmpresaAtualizacaoRequest,
    EmpresaRequest,
    EmpresaResponse,
    SituacaoRequest,
)
from meunegocio360_core.empresa.application.casos_de_uso import (
    AlterarSituacaoEmpresa,
    AtualizarEmpresa,
    CadastrarEmpresa,
    ObterEmpresaAtiva,
)
from meunegocio360_core.shared.autorizacao import TODOS_OS_PERFIS, exigir_perfil
from meunegocio360_core.shared.documentacao import exemplo_de_erro
from meunegocio360_core.shared.dominio import Perfil

PREFIXO = "/api/v1/empresa"
TAG = "Empresa"

router = APIRouter(prefix=PREFIXO, tags=[TAG])

# Matriz de autorização do RF-BE-002.
_QUALQUER_PERFIL = [Depends(exigir_perfil(*TODOS_OS_PERFIS))]
_SOMENTE_ADMIN = [Depends(exigir_perfil(Perfil.ADMIN))]


def _erro(status_http: int, code: str, descricao: str) -> dict[str, Any]:
    return exemplo_de_erro(status_http, code, descricao, PREFIXO)


_ERROS_COMUNS = {401: _erro(401, "UNAUTHORIZED", "Token ausente, inválido ou expirado")}
_ERROS_DE_ESCRITA = {
    **_ERROS_COMUNS,
    400: _erro(400, "VALIDATION_ERROR", "Campos inválidos (ex.: CNPJ com dígito errado)"),
    403: _erro(403, "ACCESS_DENIED", "Somente ADMIN altera a empresa"),
}


@router.get(
    "",
    summary="Consulta a empresa ativa",
    description="Qualquer perfil autenticado. Sem empresa ativa, responde "
    "`404 COMPANY_NOT_REGISTERED`, sinal para a interface iniciar o primeiro cadastro.",
    dependencies=_QUALQUER_PERFIL,
    responses={
        **_ERROS_COMUNS,
        404: _erro(404, "COMPANY_NOT_REGISTERED", "Não existe empresa ativa"),
    },
)
def consultar(
    caso_de_uso: Annotated[ObterEmpresaAtiva, Depends(obter_empresa_ativa)],
) -> EmpresaResponse:
    return EmpresaResponse.de(caso_de_uso.executar())


@router.post(
    "",
    summary="Cadastra a empresa (ADMIN)",
    description="A empresa é criada já **ativa**. Só pode existir uma empresa ativa e o CNPJ "
    "é único entre todas as empresas, ativas ou inativas.",
    status_code=status.HTTP_201_CREATED,
    dependencies=_SOMENTE_ADMIN,
    responses={
        **_ERROS_DE_ESCRITA,
        409: _erro(409, "COMPANY_CNPJ_DUPLICATE | COMPANY_ALREADY_ACTIVE", "Conflito"),
    },
)
def cadastrar(
    dados: EmpresaRequest,
    resposta: Response,
    caso_de_uso: Annotated[CadastrarEmpresa, Depends(cadastrar_empresa)],
) -> EmpresaResponse:
    empresa = caso_de_uso.executar(dados.para_dados())
    # A empresa cadastrada é consultada em GET /empresa (recurso único: a empresa ativa).
    resposta.headers["Location"] = PREFIXO
    return EmpresaResponse.de(empresa)


@router.put(
    "/{empresa_id}",
    summary="Edita a empresa (ADMIN)",
    description="Exige a `versao` lida (controle otimista). O CNPJ pode mudar, desde que "
    "continue único.",
    dependencies=_SOMENTE_ADMIN,
    responses={
        **_ERROS_DE_ESCRITA,
        404: _erro(404, "NOT_FOUND", "Empresa não encontrada"),
        409: _erro(409, "VERSION_CONFLICT | COMPANY_CNPJ_DUPLICATE", "Conflito"),
    },
)
def atualizar(
    empresa_id: uuid.UUID,
    dados: EmpresaAtualizacaoRequest,
    caso_de_uso: Annotated[AtualizarEmpresa, Depends(atualizar_empresa)],
) -> EmpresaResponse:
    return EmpresaResponse.de(caso_de_uso.executar(empresa_id, dados.para_dados(), dados.versao))


@router.patch(
    "/{empresa_id}/situacao",
    summary="Inativa ou reativa a empresa (ADMIN)",
    description="A empresa nunca é excluída, só inativada. Reativar com outra empresa ativa "
    "responde `409 COMPANY_ALREADY_ACTIVE`.",
    dependencies=_SOMENTE_ADMIN,
    responses={
        **_ERROS_DE_ESCRITA,
        404: _erro(404, "NOT_FOUND", "Empresa não encontrada"),
        409: _erro(409, "VERSION_CONFLICT | COMPANY_ALREADY_ACTIVE", "Conflito"),
    },
)
def alterar_situacao(
    empresa_id: uuid.UUID,
    dados: SituacaoRequest,
    caso_de_uso: Annotated[AlterarSituacaoEmpresa, Depends(alterar_situacao_empresa)],
) -> EmpresaResponse:
    return EmpresaResponse.de(caso_de_uso.executar(empresa_id, dados.ativa, dados.versao))
