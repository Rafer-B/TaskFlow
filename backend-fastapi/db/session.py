import os
from pathlib import Path
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

# O arquivo de sessao centraliza a configuracao da base de dados para SQLite
# e PostgreSQL, mantendo `SessionLocal` consistente para toda a app.
database_url = os.getenv("DATABASE_URL")
database_settings = {
    "username": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
}

if database_url:
    DATABASE_URL = database_url
elif any(database_settings.values()):
    missing_settings = [
        key for key, value in database_settings.items() if not value
    ]
    if missing_settings:
        raise RuntimeError(
            "Configuração PostgreSQL incompleta no .env. "
            f"Falta configurar: {', '.join(missing_settings)}."
        )
    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg",
        username=database_settings["username"],
        password=database_settings["password"],
        host=database_settings["host"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=database_settings["database"],
    )
else:
    DATABASE_URL = f"sqlite:///{(BASE_DIR / 'taskflow.db').as_posix()}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
    if str(DATABASE_URL).startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# `Base` e a classe-mae do SQLAlchemy para todas as entidades ORM; por ela
# a engine e os metadados ficam compartilhados em toda a aplicacao.
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
