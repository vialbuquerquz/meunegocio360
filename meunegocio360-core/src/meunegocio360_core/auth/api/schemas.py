"""DTOs de entrada e saída da API de autenticação (RNF-BE-02, RNF-BE-11, RNF-020).

Entidades de domínio nunca são devolvidas; nenhum DTO contém hash de senha ou de token.
"""

import re
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from meunegocio360_core.auth.application.comum import SessaoIniciada, UsuarioResumo

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LIMITE_SENHA_BYTES = 72  # limite do BCrypt (RN-11)


class _ModeloApi(BaseModel):
    """JSON em camelCase (RNF-BE-11)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(_ModeloApi):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "admin@meunegocio360.com.br", "senha": "********"}]
        }
    )

    email: str = Field(max_length=160)
    senha: str = Field(min_length=8, max_length=72, repr=False)

    @field_validator("email")
    @classmethod
    def _validar_email(cls, valor: str) -> str:
        valor = valor.strip()
        if not _EMAIL.match(valor):
            raise ValueError("deve ser um e-mail válido")
        return valor

    @field_validator("senha")
    @classmethod
    def _validar_bytes_senha(cls, valor: str) -> str:
        # O BCrypt considera bytes, não caracteres: letras acentuadas ocupam 2 bytes em UTF-8.
        if len(valor.encode("utf-8")) > LIMITE_SENHA_BYTES:
            raise ValueError(f"deve ter no máximo {LIMITE_SENHA_BYTES} bytes")
        return valor


class UsuarioResponse(_ModeloApi):
    id: uuid.UUID
    nome: str
    email: str
    perfil: str

    @classmethod
    def de(cls, usuario: UsuarioResumo) -> "UsuarioResponse":
        return cls(id=usuario.id, nome=usuario.nome, email=usuario.email, perfil=usuario.perfil)


class SessaoResponse(_ModeloApi):
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 - tipo do token, não é segredo
    access_token: str
    expires_in: int
    usuario: UsuarioResponse

    @classmethod
    def de(cls, sessao: SessaoIniciada) -> "SessaoResponse":
        return cls(
            access_token=sessao.access_token,
            expires_in=sessao.expira_em_segundos,
            usuario=UsuarioResponse.de(sessao.usuario),
        )
