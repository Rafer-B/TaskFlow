# ARROW4D · TaskFlow

TaskFlow é uma plataforma web para organizar projetos académicos, distribuir responsabilidades e acompanhar tarefas, prioridades, prazos e progresso.

## Funcionalidades do MVP

- Registo e início de sessão com autenticação por token.
- Criação, edição e arquivo de projetos académicos.
- Tarefas com categoria, responsável, prioridade, estado e prazo.
- Convites de membros já registados e atribuição de tarefas à equipa.
- Pesquisa e filtros por estado, prioridade e responsável.
- Indicadores de progresso, tarefas em curso e prazos ultrapassados.
- Interface responsiva em português.

## Tecnologias

- **Frontend:** Nuxt 4, Vue 3 e TypeScript.
- **Backend:** FastAPI e SQLAlchemy.
- **Base de dados:** PostgreSQL; SQLite é usado por omissão para desenvolvimento local sem configuração adicional.

## Modelo de dados

O esquema relacional cria e mantém estas tabelas:

- **`users`**: contas, email único e normalizado e hash da palavra-passe.
- **`projects`**: dados do projeto, responsável obrigatório e estado de arquivo.
- **`project_members`**: relação muitos-para-muitos entre projetos e membros, sem associações repetidas.
- **`tasks`**: tarefas associadas a um projeto, com prazo, responsável opcional, prioridade, categoria e estado validados.

As chaves estrangeiras preservam a integridade: ao remover um projeto, são removidas as suas tarefas e associações de membros, não as contas dos membros; ao remover um membro, as suas tarefas permanecem e ficam sem responsável. As categorias, estados, prioridades e campos obrigatórios também são verificados na base de dados. No arranque, o backend cria as tabelas em falta e adapta o esquema PostgreSQL antigo sem apagar os dados.

## Executar localmente

### 1. API

Requer Python 3.10 ou superior.

```powershell
cd backend-fastapi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API fica disponível em `http://localhost:8000`; a documentação interativa está em `http://localhost:8000/docs`. Sem `DATABASE_URL` nem variáveis `DB_*`, os dados ficam em `backend-fastapi/taskflow.db`.

Para usar PostgreSQL, configura no ficheiro `backend-fastapi/.env` as variáveis do formato URL:

```dotenv
DATABASE_URL=postgresql+psycopg://utilizador:palavra-passe@localhost:5432/taskflow_db
TOKEN_SECRET=um-segredo-aleatorio-longo-e-unico
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Também são aceites as variáveis `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD` existentes em instalações já configuradas; `DATABASE_URL` tem prioridade quando definida. O backend cria as tabelas no arranque sem apagar os dados existentes. Existe um modelo em [backend-fastapi/.env.example](backend-fastapi/.env.example). Usa um segredo aleatório e próprio em qualquer ambiente partilhado ou de produção.

### 2. Interface web

Numa segunda janela do PowerShell:

```powershell
cd frontend-nuxt
npm install
npm run dev
```

Abre `http://localhost:3000`. A interface comunica com a API em `http://localhost:8000`. Para alterar o endereço, define `NUXT_PUBLIC_API_BASE`.

## Verificação

Com o ambiente Python instalado, executa os testes da API a partir de `backend-fastapi`:

```powershell
python -m unittest discover -s tests -v
```

O teste rápido da ligação à base de dados também pode ser executado com `python test_db.py`.

## Estrutura

```text
backend-fastapi/
  api/routes/       Endpoints de autenticação, projetos e tarefas
  app/              Aplicação, modelos, esquemas e segurança
  db/               Configuração SQLAlchemy e sessões
  tests/            Testes de integração da API
frontend-nuxt/
  app/pages/        Interface TaskFlow
  app/composables/  Acesso à API e sessão autenticada
  app/assets/       Estilos responsivos
```

## Limites do MVP

Não inclui gestão financeira, chat em tempo real, videochamadas nem avaliação formal por docentes.
