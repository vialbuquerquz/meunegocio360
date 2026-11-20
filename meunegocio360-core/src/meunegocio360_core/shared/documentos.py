"""Validação de documentos brasileiros (RNF-BE-27): um único validador reutilizável.

Os documentos chegam e são armazenados **somente com dígitos**; a máscara é responsabilidade
do frontend.
"""

_PESOS_CNPJ_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_CNPJ_2 = (6, *_PESOS_CNPJ_1)


def _digito_verificador(base: str, pesos: tuple[int, ...]) -> int:
    resto = sum(int(digito) * peso for digito, peso in zip(base, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def somente_digitos(valor: str, tamanho: int) -> bool:
    """``True`` se ``valor`` tem exatamente ``tamanho`` dígitos ASCII (0-9)."""
    return len(valor) == tamanho and valor.isascii() and valor.isdigit()


def cnpj_valido(cnpj: str) -> bool:
    """CNPJ com 14 dígitos e dígitos verificadores corretos.

    Sequências de um único dígito repetido (``00000000000000``, ``11111111111111``...) passam
    no cálculo dos verificadores, mas não são CNPJs válidos e são rejeitadas.
    """
    if not somente_digitos(cnpj, 14) or len(set(cnpj)) == 1:
        return False
    primeiro = _digito_verificador(cnpj[:12], _PESOS_CNPJ_1)
    segundo = _digito_verificador(cnpj[:12] + str(primeiro), _PESOS_CNPJ_2)
    return cnpj[12:] == f"{primeiro}{segundo}"
