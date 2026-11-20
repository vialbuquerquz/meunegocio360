"""Documentação OpenAPI dos erros ``application/problem+json`` (RNF-BE-14, RNF-030).

Compartilhado pelas features, para que nenhuma importe os schemas internos de outra (RNF-BE-05)
e o OpenAPI tenha um único schema de problema.
"""

from typing import Any

from pydantic import BaseModel


class ErroDeCampo(BaseModel):
    field: str
    message: str


class ProblemaResponse(BaseModel):
    """Formato ``application/problem+json`` (RNF-BE-14)."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    traceId: str | None = None  # noqa: N815 - nome definido pelo contrato
    errors: list[ErroDeCampo] | None = None


def exemplo_de_erro(
    status_http: int, code: str, descricao: str, instancia: str = "/api/v1/..."
) -> dict[str, Any]:
    """Entrada de ``responses`` de uma rota, com o exemplo do erro em problem+json."""
    exemplo = {
        "type": "https://meunegocio360.com.br/problemas/...",
        "title": "...",
        "status": status_http,
        "detail": "...",
        "instance": instancia,
        "code": code,
        "traceId": "9f1c2e7a-0b6c-4a4b-9a64-2d0f1c3f6b11",
    }
    return {
        "model": ProblemaResponse,
        "description": descricao,
        "content": {"application/problem+json": {"example": exemplo}},
    }
