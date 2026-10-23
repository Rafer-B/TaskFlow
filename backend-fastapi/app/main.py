
"""Configuração da aplicação FastAPI e dos seus pontos de entrada."""

# `os` lê variáveis de ambiente; `asynccontextmanager` adapta uma função
# assíncrona com `yield` ao protocolo de ciclo de vida usado pelo FastAPI.
import os
from contextlib import asynccontextmanager

# FastAPI cria a aplicação; CORSMiddleware define que origens web podem
# comunicar com a API; `text` transforma SQL literal num objeto executável.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Importar os routers regista os endpoints de cada área. `models` é importado
# para que as classes ORM sejam conhecidas por `Base.metadata` antes da criação
# das tabelas.
from api.routes import auth, notifications, projects, tasks
from app import models
from app.migrations import upgrade_legacy_postgres_schema
from db.session import Base, engine


# O decorador converte esta função geradora assíncrona num gestor de contexto
# de ciclo de vida. FastAPI chama o código antes e depois de servir pedidos.
@asynccontextmanager
async def lifespan(_: FastAPI):
    # `create_all` cria tabelas que ainda não existem; a rotina seguinte adapta
    # esquemas PostgreSQL antigos sem apagar os dados existentes.
    Base.metadata.create_all(bind=engine)
    upgrade_legacy_postgres_schema(engine)

    # `yield` separa o arranque da aplicação do seu encerramento. `finally`
    # executa a libertação da ligação mesmo que o servidor termine com erro.
    try:
        yield
    finally:
        engine.dispose()


# Instância principal da API. Os argumentos nomeados (`chave=valor`) configuram
# documentação e versão; `lifespan` liga a rotina de arranque/encerramento.
# A aplicacao centraliza as rotas e o ciclo de vida; `lifespan` cria a base
# e valida migracoes antes dos endpoints responderem.
app = FastAPI(
    title="TaskFlow API",
    description="API para gerir projetos e tarefas académicas.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS permite que o navegador, quando a interface está noutra origem (domínio,
# protocolo ou porta), envie pedidos à API. A variável CORS_ORIGINS aceita uma
# lista separada por vírgulas; `os.getenv` usa a lista local abaixo como padrão.
# A expressão regular também permite qualquer porta em localhost/127.0.0.1.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(","),
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cada router agrupa endpoints relacionados. Incluí-los adiciona as respetivas
# rotas à aplicação sem concentrar toda a lógica neste ficheiro.
# Os routers representam modulos de dominio, mantendo o bootstrap da API
# simples e os endpoints organizados por recurso.
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(notifications.router)


# `@app.get("/")` associa esta função a pedidos HTTP GET para a raiz da API.
# `-> dict[str, str]` é uma anotação de tipo: documenta que o retorno é um
# dicionário cujas chaves e valores são strings.
@app.get("/")
def pagina_inicial() -> dict[str, str]:
    return {"mensagem": "Bem-vindo à API do TaskFlow", "estado": "online"}


# Endpoint simples de saúde. `with` gere a ligação e garante que é fechada;
# executar `SELECT 1` verifica que a base de dados responde antes de declarar
# ambos os serviços online. Se a ligação falhar, a exceção não é ocultada.
@app.get("/api/health")
def verificar_estado() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"api": "online", "database": "online"}
