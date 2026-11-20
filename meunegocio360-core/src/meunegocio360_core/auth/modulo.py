"""Interface pública da feature auth para a aplicação (RNF-BE-05): monta as dependências,
registra o router e expõe o que a aplicação precisa (verificador de token, rotas públicas,
seed e limpeza agendada)."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from fastapi import FastAPI

from meunegocio360_core.auth.api import router as api
from meunegocio360_core.auth.api.cookies import CookieDeRefresh
from meunegocio360_core.auth.api.dependencias import ContextoAuth
from meunegocio360_core.auth.api.problemas import registrar_traducoes
from meunegocio360_core.auth.application.comum import EmissorDeSessao, PoliticaDeAutenticacao
from meunegocio360_core.auth.application.manutencao import (
    LimparRefreshTokens,
    SemearUsuariosDeDesenvolvimento,
    UsuarioDeSeed,
)
from meunegocio360_core.auth.domain.usuario import Perfil
from meunegocio360_core.auth.infra.orm import mapear
from meunegocio360_core.auth.infra.repositorios import UnidadeDeTrabalhoSql
from meunegocio360_core.auth.infra.senhas import CodificadorBcrypt
from meunegocio360_core.auth.infra.tokens import GeradorDeRefreshTokenSeguro, ServicoJwt
from meunegocio360_core.shared.banco import FabricaDeSessoes
from meunegocio360_core.shared.config import Configuracao
from meunegocio360_core.shared.relogio import Relogio
from meunegocio360_core.shared.seguranca import RotaPublica, VerificadorDeToken

INTERVALO_LIMPEZA = timedelta(hours=24)

_log = logging.getLogger("meunegocio360.auth")


@dataclass(frozen=True)
class ModuloAuth:
    verificador_de_token: VerificadorDeToken
    rotas_publicas: tuple[RotaPublica, ...]
    _contexto: ContextoAuth

    def semear_usuarios_de_desenvolvimento(self, config: Configuracao) -> None:
        """RN-08 do RF-BE-002: um usuário por perfil, senhas do ambiente e nenhuma empresa."""
        senhas = (
            config.seed_admin_senha,
            config.seed_usuario_senha,
            config.seed_financeiro_senha,
        )
        if config.app_env != "dev" or not all(senhas):
            return
        admin, comercial, financeiro = (senha.get_secret_value() for senha in senhas)
        SemearUsuariosDeDesenvolvimento(
            self._contexto.nova_unidade_de_trabalho,
            self._contexto.codificador,
            self._contexto.relogio,
        ).executar(
            [
                UsuarioDeSeed("Administrador", "admin@meunegocio360.com.br", Perfil.ADMIN, admin),
                # Mesmo e-mail do antigo perfil USUARIO: em bancos existentes a migration 0003
                # já converteu esse usuário, e o seed não o duplica.
                UsuarioDeSeed(
                    "Operador Comercial",
                    "usuario@meunegocio360.com.br",
                    Perfil.OPERADOR_COMERCIAL,
                    comercial,
                ),
                UsuarioDeSeed(
                    "Operador Financeiro",
                    "financeiro@meunegocio360.com.br",
                    Perfil.OPERADOR_FINANCEIRO,
                    financeiro,
                ),
            ]
        )

    async def limpar_refresh_tokens_periodicamente(self) -> None:
        """Equivalente ao ``@Scheduled``: roda na inicialização e depois a cada 24 h."""
        caso_de_uso = LimparRefreshTokens(
            self._contexto.nova_unidade_de_trabalho, self._contexto.relogio
        )
        while True:
            try:
                await asyncio.to_thread(caso_de_uso.executar)
            except Exception:
                _log.exception("Falha na limpeza de refresh tokens")
            await asyncio.sleep(INTERVALO_LIMPEZA.total_seconds())


def configurar_auth(
    app: FastAPI, config: Configuracao, fabrica_de_sessoes: FabricaDeSessoes, relogio: Relogio
) -> ModuloAuth:
    mapear()

    politica = PoliticaDeAutenticacao(
        max_tentativas=config.app_auth_max_tentativas,
        duracao_bloqueio=timedelta(minutes=config.app_auth_bloqueio_minutos),
        validade_refresh=timedelta(days=config.app_auth_refresh_expiracao_dias),
    )
    servico_jwt = ServicoJwt(
        config.jwt_secret.get_secret_value(),
        timedelta(minutes=config.app_auth_jwt_expiracao_minutos),
    )
    gerador_de_refresh = GeradorDeRefreshTokenSeguro()
    cookie = CookieDeRefresh(
        seguro=config.app_auth_cookie_secure,
        validade_segundos=int(politica.validade_refresh.total_seconds()),
    )
    contexto = ContextoAuth(
        nova_unidade_de_trabalho=lambda: UnidadeDeTrabalhoSql(fabrica_de_sessoes),
        codificador=CodificadorBcrypt(),
        gerador_de_refresh=gerador_de_refresh,
        emissor_de_sessao=EmissorDeSessao(servico_jwt, gerador_de_refresh, politica),
        politica=politica,
        relogio=relogio,
        cookie=cookie,
        origens_permitidas=frozenset(config.cors_allowed_origins),
    )

    app.state.auth = contexto
    registrar_traducoes(cookie)
    app.include_router(api.router)

    return ModuloAuth(
        verificador_de_token=servico_jwt,
        rotas_publicas=(
            RotaPublica("POST", f"{api.PREFIXO}/login"),
            RotaPublica("POST", f"{api.PREFIXO}/refresh"),
            RotaPublica("POST", f"{api.PREFIXO}/logout"),
        ),
        _contexto=contexto,
    )
