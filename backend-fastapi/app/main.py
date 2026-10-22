
import fastapi
from fastapi import FastAPI

# Criamos a aplicação principal da API do TaskFlow.
app = fastapi.FastAPI(
    title="TaskFlow API",
    description="API para gerir projetos e tarefas académicas.",
    version="1.0.0",
)


@app.get("/")
def pagina_inicial():
    """
    Endpoint inicial para confirmar que a API funciona.
    """
    return {
        "mensagem": "Bem-vindo à API do TaskFlow",
        "estado": "online",
    }


@app.get("/api/health")
def verificar_estado():
    """
    Verifica se a aplicação está disponível.
    Nesta primeira versão ainda não testa a base de dados.
    """
    return {
        "api": "online",
    }
