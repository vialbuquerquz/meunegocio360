"""Tratamento único de erros em ``application/problem+json`` (RFC 9457) — RNF-BE-14, RNF-024.

Equivalente ao ``@RestControllerAdvice`` único: todos os erros da aplicação passam por
``registrar_tratadores``. Cada feature apenas registra como os seus erros de negócio viram
problemas HTTP (``registrar_traducao``), sem tratar exceções nos routers.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

from meunegocio360_core.shared.correlacao import CABECALHO, request_id_atual
from meunegocio360_core.shared.dominio import ErroDeNegocio, VersaoDesatualizadaError
from meunegocio360_core.shared.seguranca import aplicar_cabecalhos_seguranca

TIPO_BASE = "https://meunegocio360.com.br/problemas/"
MEDIA_TYPE = "application/problem+json"

_log = logging.getLogger("meunegocio360.erros")


@dataclass(frozen=True)
class Problema:
    status: int
    code: str
    title: str
    detail: str
    tipo: str
    errors: list[dict[str, str]] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    ajustar_resposta: Callable[[Response], None] | None = None


class ProblemaHttpError(Exception):
    """Erro da camada web que já sabe o seu formato HTTP (ex.: Origin não permitido)."""

    def __init__(self, problema: Problema) -> None:
        super().__init__(problema.code)
        self.problema = problema


def resposta_problema(problema: Problema, request: Request) -> JSONResponse:
    corpo: dict[str, Any] = {
        "type": TIPO_BASE + problema.tipo,
        "title": problema.title,
        "status": problema.status,
        "detail": problema.detail,
        "instance": request.url.path,
        "code": problema.code,
        "traceId": getattr(request.state, "request_id", None),
    }
    if problema.errors is not None:
        corpo["errors"] = problema.errors
    resposta = JSONResponse(
        corpo, status_code=problema.status, headers=problema.headers, media_type=MEDIA_TYPE
    )
    if problema.ajustar_resposta:
        problema.ajustar_resposta(resposta)
    return resposta


# --------------------------------------------------------------------------- erros de negócio

TradutorDeErro = Callable[[Any], Problema]
_traducoes: dict[type[ErroDeNegocio], TradutorDeErro] = {}


def registrar_traducao(tipo: type[ErroDeNegocio], tradutor: TradutorDeErro) -> None:
    _traducoes[tipo] = tradutor


# Erros de negócio genéricos, usados por todas as features.
registrar_traducao(
    VersaoDesatualizadaError,
    lambda _: Problema(
        409,
        "VERSION_CONFLICT",
        "Versão desatualizada",
        "O registro foi alterado por outra operação. Recarregue os dados e tente novamente.",
        "conflito-de-versao",
    ),
)


def _traduzir(erro: ErroDeNegocio) -> Problema:
    for classe in type(erro).__mro__:
        if classe in _traducoes:
            return _traducoes[classe](erro)
    return Problema(
        422,
        "BUSINESS_RULE_VIOLATION",
        "Regra de negócio violada",
        "A operação viola uma regra de negócio.",
        "regra-de-negocio",
    )


# --------------------------------------------------------------------------- validação

_MENSAGENS: dict[str, str] = {
    "missing": "campo obrigatório",
    "string_type": "deve ser um texto",
    "string_too_short": "deve ter no mínimo {min_length} caracteres",
    "string_too_long": "deve ter no máximo {max_length} caracteres",
    "json_invalid": "JSON malformado",
    "model_attributes_type": "o corpo da requisição deve ser um objeto JSON",
    "dict_type": "o corpo da requisição deve ser um objeto JSON",
}


def _mensagem(erro: dict[str, Any]) -> str:
    if erro["type"] == "value_error":
        # Mensagens próprias (em português) levantadas pelos validadores dos schemas.
        return str(erro.get("ctx", {}).get("error", "valor inválido"))
    modelo = _MENSAGENS.get(erro["type"], "valor inválido")
    try:
        return modelo.format(**erro.get("ctx", {}))
    except KeyError:
        return "valor inválido"


def _campo(local: tuple[Any, ...]) -> str:
    partes = [str(p) for p in local[1:] if not isinstance(p, int)]
    return ".".join(partes) or "body"


def _erros_de_validacao(erro: RequestValidationError) -> list[dict[str, str]]:
    return [{"field": _campo(tuple(e["loc"])), "message": _mensagem(e)} for e in erro.errors()]


# --------------------------------------------------------------------------- tratadores


def registrar_tratadores(app: FastAPI, *, producao: bool) -> None:
    @app.exception_handler(ProblemaHttpError)
    async def _problema_http(request: Request, erro: ProblemaHttpError) -> Response:
        return resposta_problema(erro.problema, request)

    @app.exception_handler(ErroDeNegocio)
    async def _negocio(request: Request, erro: ErroDeNegocio) -> Response:
        return resposta_problema(_traduzir(erro), request)

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, erro: RequestValidationError) -> Response:
        problema = Problema(
            400,
            "VALIDATION_ERROR",
            "Dados inválidos",
            "Um ou mais campos são inválidos.",
            "validacao",
            errors=_erros_de_validacao(erro),
        )
        return resposta_problema(problema, request)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, erro: StarletteHTTPException) -> Response:
        if erro.status_code == 404:
            problema = Problema(
                404,
                "NOT_FOUND",
                "Recurso não encontrado",
                "O recurso solicitado não existe.",
                "nao-encontrado",
            )
        elif erro.status_code == 405:
            problema = Problema(
                405,
                "METHOD_NOT_ALLOWED",
                "Método não permitido",
                "O método HTTP não é suportado neste recurso.",
                "metodo-nao-permitido",
                headers=dict(erro.headers or {}),
            )
        else:
            problema = Problema(
                erro.status_code,
                "HTTP_ERROR",
                "Erro na requisição",
                "A requisição não pôde ser processada.",
                "requisicao",
            )
        return resposta_problema(problema, request)

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, erro: Exception) -> Response:
        # Executado fora dos middlewares: recoloca a correlação e os cabeçalhos de segurança.
        request_id = getattr(request.state, "request_id", None)
        token = request_id_atual.set(request_id)
        try:
            _log.error("Erro inesperado", exc_info=erro)
        finally:
            request_id_atual.reset(token)
        problema = Problema(
            500,
            "INTERNAL_ERROR",
            "Erro interno",
            "Ocorreu um erro inesperado. Tente novamente mais tarde.",
            "interno",
        )
        resposta = resposta_problema(problema, request)
        if request_id:
            resposta.headers[CABECALHO] = request_id
        aplicar_cabecalhos_seguranca(resposta.headers, hsts=producao)
        return resposta
