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

- **`users`**: contas, email único e normalizado, hash da palavra-passe, perfil, curso, avatar e estado ativo.
- **`projects`**: dados, categoria/tipo, estado e datas, com criador e líder.
- **`project_types`** e **`project_models`**: tipos de projeto e modelos reutilizáveis com a estrutura das etapas em JSON.
- **`model_stages`** e **`task_stages`**: etapas ordenadas dos modelos e respetiva associação às tarefas.
- **`teams`** e **`team_members`**: equipa do projeto e respetivos membros, com papel e data de entrada.
- **`project_members`**: entidade de associação projeto-utilizador com papel e data de entrada, sem associações repetidas.
- **`stages`**: etapas opcionais associadas diretamente a projetos existentes.
- **`tasks`**: tarefas associadas a projetos, com prazo, responsável opcional, etapa opcional, prioridade, categoria e estado.
- **`comments`** e **`attachments`**: comentários e ficheiros associados a tarefas e aos respetivos autores.
- **`notifications`**: notificações associadas ao utilizador destinatário.

As chaves estrangeiras preservam a integridade: ao remover um projeto, são removidas as suas tarefas, etapas, equipa e associações de membros, não as contas dos membros; ao remover uma tarefa, são removidos os comentários, anexos e associações a etapas-modelo; ao remover um utilizador responsável por tarefas ou anexos, esses registos permanecem sem responsável. As associações de membros são únicas por projeto/equipa e utilizador. No arranque, o backend cria as tabelas em falta, converte os projetos existentes em tipos e equipas iniciais e adapta os esquemas PostgreSQL e SQLite anteriores sem apagar os dados.

A interface autenticada inclui início com indicadores, lista e detalhe de projetos, tarefas, detalhe da tarefa com comentários, equipa, notificações e calendário mensal. A atribuição de tarefas, convites e comentários geram notificações para os membros relevantes.

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

Os anexos enviados nos detalhes das tarefas têm um limite de 10 MB e são guardados em `backend-fastapi/uploads` por predefinição. Em ambientes persistentes, configura `TASKFLOW_UPLOAD_DIR` para um diretório duradouro e inclui esse diretório nas cópias de segurança.

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
