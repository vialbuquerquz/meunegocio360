"""Casos de uso da empresa (RF-BE-002, "Contrato da API" e "Regras de negócio").

A autorização por perfil (RN-03) é aplicada nas rotas; aqui ficam as regras de negócio. As
unicidades (RN-01, RN-02) são checadas antes para devolver o erro certo, e o banco as garante
de novo (índices únicos) contra condições de corrida.
"""

import uuid

from meunegocio360_core.empresa.application.comum import EmpresaResumo, FabricaDeUnidadeDeTrabalho
from meunegocio360_core.empresa.domain.empresa import DadosDaEmpresa, Empresa
from meunegocio360_core.empresa.domain.erros import (
    CnpjDuplicadoError,
    EmpresaJaAtivaError,
    EmpresaNaoCadastradaError,
    EmpresaNaoEncontradaError,
)
from meunegocio360_core.empresa.domain.portas import RepositorioDeEmpresas
from meunegocio360_core.shared.relogio import Relogio


def _buscar_para_alterar(repositorio: RepositorioDeEmpresas, empresa_id: uuid.UUID) -> Empresa:
    empresa = repositorio.buscar_por_id_para_atualizacao(empresa_id)
    if empresa is None:
        raise EmpresaNaoEncontradaError
    return empresa


class ObterEmpresaAtiva:
    """``GET /empresa``: a empresa ativa ou ``COMPANY_NOT_REGISTERED``."""

    def __init__(self, nova_unidade_de_trabalho: FabricaDeUnidadeDeTrabalho) -> None:
        self._nova_uow = nova_unidade_de_trabalho

    def executar(self) -> EmpresaResumo:
        with self._nova_uow() as uow:
            empresa = uow.empresas.buscar_ativa()
            if empresa is None:
                raise EmpresaNaoCadastradaError
            return EmpresaResumo.de(empresa)


class CadastrarEmpresa:
    """``POST /empresa``: cria a empresa já ativa (RN-01, RN-02)."""

    def __init__(self, nova_unidade_de_trabalho: FabricaDeUnidadeDeTrabalho, relogio: Relogio):
        self._nova_uow = nova_unidade_de_trabalho
        self._relogio = relogio

    def executar(self, dados: DadosDaEmpresa) -> EmpresaResumo:
        with self._nova_uow() as uow:
            # CNPJ duplicado é checado primeiro: cadastrar o mesmo CNPJ da empresa ativa deve
            # responder COMPANY_CNPJ_DUPLICATE (critérios de aceite).
            if uow.empresas.existe_cnpj(dados.cnpj):
                raise CnpjDuplicadoError
            if uow.empresas.buscar_ativa() is not None:
                raise EmpresaJaAtivaError
            empresa = Empresa.cadastrar(dados, self._relogio.agora())
            uow.empresas.adicionar(empresa)
            uow.commit()
            return EmpresaResumo.de(empresa)


class AtualizarEmpresa:
    """``PUT /empresa/{id}``: edita os dados, exigindo a versão lida (RN-06). O CNPJ pode mudar."""

    def __init__(self, nova_unidade_de_trabalho: FabricaDeUnidadeDeTrabalho, relogio: Relogio):
        self._nova_uow = nova_unidade_de_trabalho
        self._relogio = relogio

    def executar(self, empresa_id: uuid.UUID, dados: DadosDaEmpresa, versao: int) -> EmpresaResumo:
        with self._nova_uow() as uow:
            empresa = _buscar_para_alterar(uow.empresas, empresa_id)
            empresa.conferir_versao(versao)
            if dados.cnpj != empresa.cnpj and uow.empresas.existe_cnpj(
                dados.cnpj, exceto_id=empresa.id
            ):
                raise CnpjDuplicadoError
            empresa.atualizar(dados, self._relogio.agora())
            uow.commit()
            return EmpresaResumo.de(empresa)


class AlterarSituacaoEmpresa:
    """``PATCH /empresa/{id}/situacao``: inativa ou reativa (RN-02, RN-04)."""

    def __init__(self, nova_unidade_de_trabalho: FabricaDeUnidadeDeTrabalho, relogio: Relogio):
        self._nova_uow = nova_unidade_de_trabalho
        self._relogio = relogio

    def executar(self, empresa_id: uuid.UUID, ativa: bool, versao: int) -> EmpresaResumo:
        with self._nova_uow() as uow:
            empresa = _buscar_para_alterar(uow.empresas, empresa_id)
            empresa.conferir_versao(versao)
            if empresa.ativa == ativa:  # já está na situação pedida: nada a alterar
                return EmpresaResumo.de(empresa)
            agora = self._relogio.agora()
            if ativa:
                if uow.empresas.existe_outra_ativa(empresa.id):
                    raise EmpresaJaAtivaError
                empresa.reativar(agora)
            else:
                empresa.inativar(agora)
            uow.commit()
            return EmpresaResumo.de(empresa)
