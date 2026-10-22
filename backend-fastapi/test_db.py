
from sqlalchemy import text

from db.session import engine

with engine.connect() as connection:
    assert connection.execute(text("SELECT 1")).scalar_one() == 1

print("Ligação à base de dados estabelecida com sucesso!")
