"""Endpoints de autenticação (RF-BE-001, "Contrato da API").

Routers finos (RNF-BE-01): recebem o DTO, chamam um caso de uso e devolvem o DTO. Não há
regra de negócio nem tratamento de exceção aqui; os erros viram problem+json no tratador único.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Response, status

from meunegocio360_core.auth.api import cookies
from meunegocio360_core.auth.api.cookies import CookieDeRefresh
from meunegocio360_core.auth.api.dependencias import (
    autenticar,
    cookie_de_refresh,
    encerrar_sessao,
    obter_usuario_atual,
    renovar_sessao,
    usuario_autenticado,
    verificar_origem,
)
from meunegocio360_core.auth.api.schemas import LoginRequest, SessaoResponse, UsuarioResponse
from meunegocio360_core.auth.application.autenticar import Autenticar
from meunegocio360_core.auth.application.encerrar_sessao import EncerrarSessao
from meunegocio360_core.auth.application.obter_usuario_atual import ObterUsuarioAtual
from meunegocio360_core.auth.application.renovar_sessao import RenovarSessao
from meunegocio360_core.shared.documentacao import exemplo_de_erro
from meunegocio360_core.shared.seguranca import Principal

PREFIXO = "/api/v1/auth"

router = APIRouter(prefix=PREFIXO, tags=["Autenticação"])

CookieRefresh = Annotated[str | None, Cookie(alias=cookies.NOME, include_in_schema=False)]


def _erro(status_http: int, code: str, descricao: str) -> dict[str, Any]:
    return exemplo_de_erro(status_http, code, descricao, f"{PREFIXO}/...")


@router.post(
    "/login",
    summary="Autentica por e-mail e senha",
    description="Devolve o token de acesso no corpo e o refresh token no cookie "
    f"`{cookies.NOME}` (HttpOnly, SameSite=Strict, Path={cookies.CAMINHO}).",
    responses={
        400: _erro(400, "VALIDATION_ERROR", "Dados inválidos"),
        401: _erro(401, "INVALID_CREDENTIALS", "E-mail ou senha inválidos"),
        429: _erro(429, "ACCOUNT_TEMPORARILY_LOCKED", "Conta bloqueada (ver Retry-After)"),
    },
)
def login(
    dados: LoginRequest,
    resposta: Response,
    caso_de_uso: Annotated[Autenticar, Depends(autenticar)],
    cookie: Annotated[CookieDeRefresh, Depends(cookie_de_refresh)],
) -> SessaoResponse:
    sessao = caso_de_uso.executar(dados.email, dados.senha)
    cookie.gravar(resposta, sessao.refresh_token)
    return SessaoResponse.de(sessao)


@router.post(
    "/refresh",
    summary="Renova a sessão (rotação do refresh token)",
    description=f"Usa o cookie `{cookies.NOME}`, enviado automaticamente pelo navegador.",
    dependencies=[Depends(verificar_origem)],
    responses={
        401: _erro(401, "INVALID_REFRESH_TOKEN", "Refresh token ausente ou inválido"),
        403: _erro(403, "ORIGIN_NOT_ALLOWED", "Origem não permitida"),
    },
)
def refresh(
    resposta: Response,
    caso_de_uso: Annotated[RenovarSessao, Depends(renovar_sessao)],
    cookie: Annotated[CookieDeRefresh, Depends(cookie_de_refresh)],
    refresh_token: CookieRefresh = None,
) -> SessaoResponse:
    sessao = caso_de_uso.executar(refresh_token)
    cookie.gravar(resposta, sessao.refresh_token)
    return SessaoResponse.de(sessao)


@router.post(
    "/logout",
    summary="Encerra a sessão (idempotente)",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(verificar_origem)],
    responses={403: _erro(403, "ORIGIN_NOT_ALLOWED", "Origem não permitida")},
)
def logout(
    caso_de_uso: Annotated[EncerrarSessao, Depends(encerrar_sessao)],
    cookie: Annotated[CookieDeRefresh, Depends(cookie_de_refresh)],
    refresh_token: CookieRefresh = None,
) -> Response:
    caso_de_uso.executar(refresh_token)
    resposta = Response(status_code=status.HTTP_204_NO_CONTENT)
    cookie.limpar(resposta)
    return resposta


@router.get(
    "/me",
    summary="Dados do usuário autenticado",
    responses={401: _erro(401, "UNAUTHORIZED", "Token ausente, inválido ou expirado")},
)
def me(
    principal: Annotated[Principal, Depends(usuario_autenticado)],
    caso_de_uso: Annotated[ObterUsuarioAtual, Depends(obter_usuario_atual)],
) -> UsuarioResponse:
    return UsuarioResponse.de(caso_de_uso.executar(principal.usuario_id))
