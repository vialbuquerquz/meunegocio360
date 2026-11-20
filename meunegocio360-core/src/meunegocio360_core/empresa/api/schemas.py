"""DTOs de entrada e saída da API da empresa (RNF-BE-02, RNF-BE-11, RNF-020).

As validações espelham o contrato do RF-BE-002 ("POST /empresa") e as regras RN-01, RN-05 e
RN-06. Mensagens em português; o campo do erro usa o nome do contrato (camelCase).
"""

import re
import uuid
import zoneinfo
from datetime import UTC, datetime
from functools import cache

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic.alias_generators import to_camel

from meunegocio360_core.empresa.application.comum import EmpresaResumo
from meunegocio360_core.empresa.domain.empresa import (
    FUSO_HORARIO_PADRAO,
    MOEDA_PADRAO,
    DadosDaEmpresa,
)
from meunegocio360_core.shared.documentos import cnpj_valido, somente_digitos

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOEDAS_ACEITAS = frozenset({MOEDA_PADRAO})  # RN-05: nesta fase, somente BRL


@cache
def _fusos_iana() -> frozenset[str]:
    return frozenset(zoneinfo.available_timezones())


def _opcional(valor: str | None) -> str | None:
    """Texto opcional com *trim*; vazio equivale a não informado (RN-06)."""
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class _ModeloApi(BaseModel):
    """JSON em camelCase (RNF-BE-11)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class EmpresaRequest(_ModeloApi):
    """Corpo do ``POST /empresa``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "razaoSocial": "Comércio Exemplo Ltda",
                    "nomeFantasia": "Exemplo Informática",
                    "cnpj": "11222333000181",
                    "email": "contato@exemplo.com.br",
                    "telefone": "11987654321",
                    "fusoHorario": "America/Sao_Paulo",
                    "moeda": "BRL",
                }
            ]
        }
    )

    razao_social: str = Field(description="Obrigatória, de 3 a 150 caracteres.")
    nome_fantasia: str | None = Field(default=None, description="Opcional, até 150 caracteres.")
    cnpj: str = Field(description="14 dígitos, sem máscara, com dígitos verificadores válidos.")
    email: str | None = Field(default=None, description="Opcional, até 160 caracteres.")
    telefone: str | None = Field(default=None, description="Opcional, 10 ou 11 dígitos.")
    fuso_horario: str | None = Field(
        default=None, description=f"Identificador IANA. Padrão: `{FUSO_HORARIO_PADRAO}`."
    )
    moeda: str | None = Field(default=None, description=f"Somente `{MOEDA_PADRAO}` nesta fase.")

    @field_validator("razao_social")
    @classmethod
    def _validar_razao_social(cls, valor: str) -> str:
        valor = valor.strip()
        if not 3 <= len(valor) <= 150:
            raise ValueError("deve ter entre 3 e 150 caracteres")
        return valor

    @field_validator("nome_fantasia")
    @classmethod
    def _validar_nome_fantasia(cls, valor: str | None) -> str | None:
        valor = _opcional(valor)
        if valor is not None and len(valor) > 150:
            raise ValueError("deve ter no máximo 150 caracteres")
        return valor

    @field_validator("cnpj")
    @classmethod
    def _validar_cnpj(cls, valor: str) -> str:
        # RN-01 e RNF-BE-27: somente dígitos (a máscara é do frontend) e verificadores corretos.
        valor = valor.strip()
        if not somente_digitos(valor, 14):
            raise ValueError("deve ter 14 dígitos, sem pontuação")
        if not cnpj_valido(valor):
            raise ValueError("deve ser um CNPJ válido")
        return valor

    @field_validator("email")
    @classmethod
    def _validar_email(cls, valor: str | None) -> str | None:
        valor = _opcional(valor)
        if valor is not None and (len(valor) > 160 or not _EMAIL.match(valor)):
            raise ValueError("deve ser um e-mail válido com até 160 caracteres")
        return valor

    @field_validator("telefone")
    @classmethod
    def _validar_telefone(cls, valor: str | None) -> str | None:
        valor = _opcional(valor)
        if valor is not None and not (somente_digitos(valor, 10) or somente_digitos(valor, 11)):
            raise ValueError("deve ter 10 ou 11 dígitos, sem pontuação")
        return valor

    @field_validator("fuso_horario")
    @classmethod
    def _validar_fuso_horario(cls, valor: str | None) -> str:
        valor = _opcional(valor)
        if valor is None:
            return FUSO_HORARIO_PADRAO
        if valor not in _fusos_iana():  # RN-05: identificador IANA válido
            raise ValueError("deve ser um fuso horário IANA válido (ex.: America/Sao_Paulo)")
        return valor

    @field_validator("moeda")
    @classmethod
    def _validar_moeda(cls, valor: str | None) -> str:
        valor = _opcional(valor)
        if valor is None:
            return MOEDA_PADRAO
        if valor not in MOEDAS_ACEITAS:
            raise ValueError(f"nesta fase, somente {MOEDA_PADRAO}")
        return valor

    def para_dados(self) -> DadosDaEmpresa:
        return DadosDaEmpresa(
            razao_social=self.razao_social,
            nome_fantasia=self.nome_fantasia,
            cnpj=self.cnpj,
            email=self.email,
            telefone=self.telefone,
            fuso_horario=self.fuso_horario or FUSO_HORARIO_PADRAO,
            moeda=self.moeda or MOEDA_PADRAO,
        )


class EmpresaAtualizacaoRequest(EmpresaRequest):
    """Corpo do ``PUT /empresa/{id}``: os campos do cadastro mais a ``versao`` lida (RN-06)."""

    versao: int = Field(ge=0, description="Versão lida no último GET (controle otimista).")


class SituacaoRequest(_ModeloApi):
    """Corpo do ``PATCH /empresa/{id}/situacao``."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"ativa": False, "versao": 3}]})

    ativa: bool
    versao: int = Field(ge=0)


class EmpresaResponse(_ModeloApi):
    id: uuid.UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str
    email: str | None
    telefone: str | None
    fuso_horario: str
    moeda: str
    ativa: bool
    criado_em: datetime
    atualizado_em: datetime
    versao: int

    @field_serializer("criado_em", "atualizado_em")
    def _em_utc(self, instante: datetime) -> str:
        """RNF-033: ISO 8601 em UTC (``2026-11-18T14:30:00Z``), seja qual for o fuso do banco."""
        return instante.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @classmethod
    def de(cls, empresa: EmpresaResumo) -> "EmpresaResponse":
        return cls(
            id=empresa.id,
            razao_social=empresa.razao_social,
            nome_fantasia=empresa.nome_fantasia,
            cnpj=empresa.cnpj,
            email=empresa.email,
            telefone=empresa.telefone,
            fuso_horario=empresa.fuso_horario,
            moeda=empresa.moeda,
            ativa=empresa.ativa,
            criado_em=empresa.criado_em,
            atualizado_em=empresa.atualizado_em,
            versao=empresa.versao,
        )
