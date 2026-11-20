"""Autorização por perfil nos endpoints (RF-BE-002, RNF-BE-47).

A autenticação (token válido) já foi feita pelo ``ExigirAutenticacaoMiddleware``; aqui só se
decide se o perfil do usuário pode executar a operação, conforme a matriz de cada RF. Isso vale
apenas no servidor: perfis checados só no frontend não protegem nada.

Uso em uma rota::

    @router.post("", dependencies=[Depends(exigir_perfil(Perfil.ADMIN))])
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from meunegocio360_core.shared.dominio import Perfil
from meunegocio360_core.shared.erros import Problema, ProblemaHttpError
from meunegocio360_core.shared.seguranca import Principal

ACESSO_NEGADO = Problema(
    403,
    "ACCESS_DENIED",
    "Acesso negado",
    "Seu perfil não tem permissão para executar esta operação.",
    "acesso-negado",
)

_NAO_AUTENTICADO = Problema(
    401,
    "UNAUTHORIZED",
    "Não autenticado",
    "Token de acesso ausente, inválido ou expirado.",
    "nao-autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)

# Só documenta o esquema Bearer no OpenAPI (botão "Authorize" do Swagger); a validação do
# token é feita antes, pelo middleware de negação por padrão.
_esquema_bearer = HTTPBearer(auto_error=False, description="Token de acesso (JWT)")

TODOS_OS_PERFIS = tuple(Perfil)


def principal_autenticado(
    request: Request,
    _credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
) -> Principal:
    principal = getattr(request.state, "principal", None)
    if principal is None:  # só ocorre se a rota for pública por engano
        raise ProblemaHttpError(_NAO_AUTENTICADO)
    return principal


def exigir_perfil(*perfis: Perfil) -> Callable[..., Principal]:
    """Dependência que responde ``403 ACCESS_DENIED`` se o perfil não estiver em ``perfis``."""
    permitidos = frozenset(str(perfil) for perfil in perfis)

    def _verificar(principal: Annotated[Principal, Depends(principal_autenticado)]) -> Principal:
        if principal.perfil not in permitidos:
            raise ProblemaHttpError(ACESSO_NEGADO)
        return principal

    return _verificar
