
from db.session import testar_ligacao

if testar_ligacao():
    print("Ligação ao PostgreSQL estabelecida com sucesso!")
