
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Localiza o ficheiro .env na raiz do backend
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# Lê as configurações da base de dados
db_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)

# Cria a ligação à base de dados
engine = create_engine(db_url, pool_pre_ping=True)


def testar_ligacao() -> bool:
    """Verifica se conseguimos executar uma consulta."""
    with engine.connect() as connection:
        resultado = connection.execute(text("SELECT 1"))
        return resultado.scalar_one() == 1
