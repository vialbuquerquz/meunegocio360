"""Tipos de domínio compartilhados, sem dependência de HTTP nem de banco."""

from enum import StrEnum


class ErroDeNegocio(Exception):
    """Base das violações de regra de negócio. A tradução para HTTP fica na camada ``api``."""


class VersaoDesatualizadaError(ErroDeNegocio):
    """Controle otimista (RNF-BE-28): a ``versao`` enviada não é a atual do registro."""


class Perfil(StrEnum):
    """Perfis de acesso (RF-BE-002, RN-07), gravados na claim ``perfil`` do JWT."""

    ADMIN = "ADMIN"
    OPERADOR_COMERCIAL = "OPERADOR_COMERCIAL"
    OPERADOR_FINANCEIRO = "OPERADOR_FINANCEIRO"
