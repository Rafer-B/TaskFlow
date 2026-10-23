
# Este script minimo serve de smoke test de conexao: confirma que a engine
# consegue abrir uma sessao e executar uma query simples.
from sqlalchemy import text

from db.session import engine

with engine.connect() as connection:
    assert connection.execute(text("SELECT 1")).scalar_one() == 1

print("Ligação à base de dados estabelecida com sucesso!")
