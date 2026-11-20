"""``EmpresaAtiva``: resolução do ``empresa_id`` no servidor (RF-BE-002, RNF-096).

É a interface pública que os demais requisitos (RF-BE-003 em diante) usam para obter a empresa
das suas entidades de negócio. O ``empresa_id`` NUNCA vem do cliente: vem daqui. Sem empresa
ativa, a operação de negócio é recusada com ``422 COMPANY_NOT_ACTIVE`` (RN-04).

Uso previsto num caso de uso de outra feature (RNF-BE-05: nenhuma feature acessa o repositório
da empresa diretamente)::

    empresa_id = self._empresa_ativa.obter_id()
"""

import uuid

from meunegocio360_core.empresa.application.comum import FabricaDeUnidadeDeTrabalho
from meunegocio360_core.empresa.domain.erros import EmpresaNaoAtivaError


class EmpresaAtiva:
    def __init__(self, nova_unidade_de_trabalho: FabricaDeUnidadeDeTrabalho) -> None:
        self._nova_uow = nova_unidade_de_trabalho

    def obter_id(self) -> uuid.UUID:
        """``id`` da empresa ativa; lança ``EmpresaNaoAtivaError`` se não houver."""
        with self._nova_uow() as uow:
            empresa = uow.empresas.buscar_ativa()
            if empresa is None:
                raise EmpresaNaoAtivaError
            return empresa.id
