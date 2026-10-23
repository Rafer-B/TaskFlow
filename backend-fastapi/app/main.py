
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.routes import auth, notifications, projects, tasks
from app import models
from app.migrations import upgrade_legacy_postgres_schema
from db.session import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    upgrade_legacy_postgres_schema(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="TaskFlow API",
    description="API para gerir projetos e tarefas académicas.",
    version="1.0.0",
    lifespan=lifespan,
)
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
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(notifications.router)


@app.get("/")
def pagina_inicial() -> dict[str, str]:
    return {"mensagem": "Bem-vindo à API do TaskFlow", "estado": "online"}


@app.get("/api/health")
def verificar_estado() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"api": "online", "database": "online"}
