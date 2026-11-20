"""Interface pública da feature empresa para a aplicação (RNF-BE-05): monta as dependências,
registra o router e expõe ``EmpresaAtiva`` para os demais requisitos."""

from dataclasses import dataclass

from fastapi import FastAPI

from meunegocio360_core.empresa.api import router as api
from meunegocio360_core.empresa.api.dependencias import ContextoEmpresa
from meunegocio360_core.empresa.api.problemas import registrar_traducoes
from meunegocio360_core.empresa.application.empresa_ativa import EmpresaAtiva
from meunegocio360_core.empresa.infra.orm import mapear
from meunegocio360_core.empresa.infra.repositorios import UnidadeDeTrabalhoSql
from meunegocio360_core.shared.banco import FabricaDeSessoes
from meunegocio360_core.shared.relogio import Relogio

TAG_OPENAPI = {
    "name": api.TAG,
    "description": (
        "Cadastro da empresa e parâmetros básicos (RF-BE-002). Só pode existir **uma empresa "
        "ativa**; somente `ADMIN` cadastra, edita, inativa e reativa, e qualquer perfil "
        "consulta.\n\n"
        "**Mecanismo `EmpresaAtiva` (RNF-096):** as entidades de negócio dos próximos "
        "requisitos (clientes, fornecedores, catálogo...) pertencem à empresa ativa, resolvida "
        "no servidor; o `empresaId` nunca é enviado pelo cliente. Sem empresa ativa, toda "
        "operação de criação desses recursos responde `422` com `code` `COMPANY_NOT_ACTIVE`."
    ),
}


@dataclass(frozen=True)
class ModuloEmpresa:
    empresa_ativa: EmpresaAtiva


def configurar_empresa(
    app: FastAPI, fabrica_de_sessoes: FabricaDeSessoes, relogio: Relogio
) -> ModuloEmpresa:
    mapear()

    def nova_unidade_de_trabalho() -> UnidadeDeTrabalhoSql:
        return UnidadeDeTrabalhoSql(fabrica_de_sessoes)

    empresa_ativa = EmpresaAtiva(nova_unidade_de_trabalho)
    app.state.empresa = ContextoEmpresa(
        nova_unidade_de_trabalho=nova_unidade_de_trabalho,
        relogio=relogio,
        empresa_ativa=empresa_ativa,
    )
    registrar_traducoes()
    app.include_router(api.router)

    return ModuloEmpresa(empresa_ativa=empresa_ativa)
