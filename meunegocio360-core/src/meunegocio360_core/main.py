"""Criação da aplicação FastAPI do Núcleo.

Executar com ``uvicorn --factory meunegocio360_core.main:create_app``: a configuração é lida
(e validada) na criação, então a aplicação não sobe se faltar uma variável obrigatória.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from meunegocio360_core.auth.modulo import configurar_auth
from meunegocio360_core.empresa.modulo import TAG_OPENAPI as TAG_EMPRESA
from meunegocio360_core.empresa.modulo import configurar_empresa
from meunegocio360_core.shared import saude
from meunegocio360_core.shared.banco import criar_fabrica_de_sessoes
from meunegocio360_core.shared.config import Configuracao, carregar_configuracao
from meunegocio360_core.shared.correlacao import CABECALHO, CorrelacaoMiddleware
from meunegocio360_core.shared.erros import registrar_tratadores
from meunegocio360_core.shared.logs import configurar_logs
from meunegocio360_core.shared.relogio import RelogioDoSistema
from meunegocio360_core.shared.seguranca import (
    CabecalhosSegurancaMiddleware,
    ExigirAutenticacaoMiddleware,
    RotaPublica,
)

SWAGGER_UI = "/swagger-ui.html"
OPENAPI = "/openapi.json"


def create_app(config: Configuracao | None = None) -> FastAPI:
    config = config or carregar_configuracao()
    configurar_logs(estruturado=config.app_env != "dev")
    fabrica_de_sessoes = criar_fabrica_de_sessoes(config)

    @contextlib.asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        await asyncio.to_thread(modulo_auth.semear_usuarios_de_desenvolvimento, config)
        limpeza = asyncio.create_task(modulo_auth.limpar_refresh_tokens_periodicamente())
        try:
            yield
        finally:
            limpeza.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await limpeza

    # RNF-030: Swagger UI e OpenAPI somente fora de produção.
    app = FastAPI(
        title="MeuNegocio360 - Núcleo",
        version="0.1.0",
        docs_url=None if config.producao else SWAGGER_UI,
        openapi_url=None if config.producao else OPENAPI,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        openapi_tags=[TAG_EMPRESA],
        lifespan=ciclo_de_vida,
    )
    app.state.fabrica_de_sessoes = fabrica_de_sessoes

    relogio = RelogioDoSistema()
    modulo_auth = configurar_auth(app, config, fabrica_de_sessoes, relogio)
    configurar_empresa(app, fabrica_de_sessoes, relogio)
    app.include_router(saude.router)
    registrar_tratadores(app, producao=config.producao)

    # Lista explícita do que é público (RNF-021, RNF-BE-40); todo o resto exige token.
    publicas = [RotaPublica("GET", saude.CAMINHO), *modulo_auth.rotas_publicas]
    if not config.producao:
        publicas += [RotaPublica("GET", SWAGGER_UI), RotaPublica("GET", OPENAPI)]

    # Ordem de execução (de fora para dentro): correlação -> cabeçalhos -> CORS -> autenticação.
    app.add_middleware(
        ExigirAutenticacaoMiddleware,
        verificador=modulo_auth.verificador_de_token,
        publicas=publicas,
    )
    app.add_middleware(
        CORSMiddleware,  # RNF-BE-42: origens explícitas, com credenciais, sem curinga
        allow_origins=config.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", CABECALHO],
        expose_headers=[CABECALHO, "Retry-After", "WWW-Authenticate"],
    )
    app.add_middleware(CabecalhosSegurancaMiddleware, hsts=config.producao)
    app.add_middleware(CorrelacaoMiddleware)

    return app
