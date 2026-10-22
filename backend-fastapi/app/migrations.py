from collections.abc import Sequence

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.models import Base


PROJECT_CATEGORIES = (
    "Investigação",
    "Desenvolvimento",
    "Seminário",
    "Estudo de caso",
    "Outro",
)
TASK_CATEGORIES = (
    "Planeamento",
    "Pesquisa",
    "Conceção",
    "Execução",
    "Validação",
    "Documentação",
)
TASK_STATUSES = ("todo", "in_progress", "done", "blocked")
TASK_PRIORITIES = ("low", "medium", "high")


def _ensure_foreign_key(
    engine: Engine,
    table: str,
    column: str,
    referred_table: str,
    referred_column: str,
    on_delete: str | None = None,
) -> None:
    inspector = inspect(engine)
    for constraint in inspector.get_foreign_keys(table):
        if (
            constraint["constrained_columns"] == [column]
            and constraint["referred_table"] == referred_table
            and constraint["referred_columns"] == [referred_column]
            and constraint.get("options", {}).get("ondelete", "").upper()
            == (on_delete or "").upper()
        ):
            return
        if constraint["constrained_columns"] == [column]:
            constraint_name = constraint.get("name")
            if constraint_name:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            f'ALTER TABLE "{table}" DROP CONSTRAINT "{constraint_name}"'
                        )
                    )

    constraint_name = f"fk_{table}_{column}_{referred_table}"
    delete_clause = f" ON DELETE {on_delete}" if on_delete else ""
    with engine.begin() as connection:
        connection.execute(
            text(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{constraint_name}" '
                f'FOREIGN KEY ("{column}") REFERENCES "{referred_table}" '
                f'("{referred_column}"){delete_clause}'
            )
        )


def _ensure_check(
    engine: Engine,
    table: str,
    constraint_name: str,
    accepted_values: Sequence[str],
    expression: str,
) -> None:
    checks = inspect(engine).get_check_constraints(table)
    for constraint in checks:
        if constraint.get("name") == constraint_name:
            return

    column = constraint_name.removeprefix(f"ck_{table}_")
    for constraint in checks:
        if constraint.get("name") in {
            f"{table}_{column}_check",
            f"{table}_{column}_check1",
        }:
            old_name = constraint["name"]
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f'ALTER TABLE "{table}" DROP CONSTRAINT "{old_name}"'
                    )
                )

    with engine.begin() as connection:
            if accepted_values:
                quoted_values = ", ".join(
                    "'" + value.replace("'", "''") + "'" for value in accepted_values
                )
                connection.execute(
                    text(
                        f'UPDATE "{table}" SET "{column}" = CASE lower("{column}") '
                        f"WHEN 'baixa' THEN 'low' WHEN 'media' THEN 'medium' "
                        f"WHEN 'média' THEN 'medium' WHEN 'alta' THEN 'high' "
                        f"WHEN 'pendente' THEN 'todo' WHEN 'em_progresso' THEN 'in_progress' "
                        f"WHEN 'concluida' THEN 'done' WHEN 'concluída' THEN 'done' "
                        f"WHEN 'bloqueada' THEN 'blocked' ELSE \"{column}\" END "
                        f'WHERE "{column}" NOT IN ({quoted_values})'
                    )
                )
                invalid_values = connection.execute(
                    text(
                        f'SELECT DISTINCT "{column}" FROM "{table}" '
                        f'WHERE "{column}" NOT IN ({quoted_values})'
                    )
                ).scalars().all()
                if invalid_values:
                    raise RuntimeError(
                        f"A tabela {table} contém valores inválidos em {column}: "
                        f"{', '.join(map(str, invalid_values))}."
                    )
            connection.execute(
            text(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{constraint_name}" '
                f"CHECK ({expression})"
            )
            )


def _ensure_index(
    engine: Engine,
    name: str,
    ddl: str,
    table: str,
    columns: Sequence[str] = (),
    unique: bool = False,
) -> None:
    indexes = inspect(engine).get_indexes(table)
    for index in indexes:
        index_columns = tuple(index.get("column_names") or ())
        if index["name"] == name:
            if index["unique"] != unique or (columns and index_columns != tuple(columns)):
                raise RuntimeError(
                    f"O índice {name} em {table} não corresponde à definição necessária."
                )
            return
        if columns and index_columns == tuple(columns) and index["unique"] == unique:
            return
    with engine.begin() as connection:
        connection.execute(text(ddl))


def upgrade_legacy_postgres_schema(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = set(Base.metadata.tables)
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Não foi possível inicializar todas as tabelas: "
            f"{', '.join(sorted(missing_tables))}."
        )

    project_columns = {
        column["name"] for column in inspector.get_columns("projects")
    }
    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    project_additions = {
        "category": "VARCHAR(40) NOT NULL DEFAULT 'Desenvolvimento'",
        "color": "VARCHAR(20) NOT NULL DEFAULT '#6c63ff'",
        "archived": "BOOLEAN NOT NULL DEFAULT FALSE",
        "owner_id": "INTEGER",
    }
    task_additions = {
        "category": "VARCHAR(40) NOT NULL DEFAULT 'Execução'",
        "deadline": "DATE",
        "assignee_id": "INTEGER",
    }

    with engine.begin() as connection:
        for column, definition in project_additions.items():
            if column not in project_columns:
                connection.execute(
                    text(f"ALTER TABLE projects ADD COLUMN {column} {definition}")
                )
        for column, definition in task_additions.items():
            if column not in task_columns:
                connection.execute(
                    text(f"ALTER TABLE tasks ADD COLUMN {column} {definition}")
                )

        if "due_date" in task_columns:
            connection.execute(
                text(
                    "UPDATE tasks SET deadline = due_date "
                    "WHERE deadline IS NULL AND due_date IS NOT NULL"
                )
            )
        connection.execute(
            text("UPDATE projects SET description = '' WHERE description IS NULL")
        )
        connection.execute(
            text("UPDATE tasks SET description = '' WHERE description IS NULL")
        )
        connection.execute(
            text("UPDATE projects SET archived = FALSE WHERE archived IS NULL")
        )

        duplicate_emails = connection.execute(
            text(
                "SELECT lower(trim(email)) FROM users "
                "GROUP BY lower(trim(email)) HAVING COUNT(*) > 1"
            )
        ).scalars().all()
        if duplicate_emails:
            raise RuntimeError(
                "Existem contas com emails duplicados sem diferenciar "
                "maiúsculas/minúsculas: " + ", ".join(duplicate_emails)
            )
        connection.execute(
            text("UPDATE users SET email = lower(trim(email))")
        )

        missing_owners = connection.execute(
            text(
                "SELECT p.id FROM projects p "
                "LEFT JOIN users u ON u.id = p.owner_id "
                "WHERE p.owner_id IS NULL OR u.id IS NULL LIMIT 10"
            )
        ).scalars().all()
        if missing_owners:
            raise RuntimeError(
                "Há projetos sem um proprietário válido (IDs: "
                + ", ".join(map(str, missing_owners))
                + "). Associe-os a um utilizador antes de concluir a migração."
            )

        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN name TYPE VARCHAR(160)")
        )
        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN description SET DEFAULT ''")
        )
        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN description SET NOT NULL")
        )
        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN category SET DEFAULT 'Desenvolvimento'")
        )
        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN color SET DEFAULT '#6c63ff'")
        )
        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN archived SET DEFAULT FALSE")
        )
        connection.execute(
            text("ALTER TABLE projects ALTER COLUMN owner_id SET NOT NULL")
        )
        connection.execute(
            text("ALTER TABLE tasks ALTER COLUMN description SET DEFAULT ''")
        )
        connection.execute(
            text("ALTER TABLE tasks ALTER COLUMN description SET NOT NULL")
        )
        connection.execute(
            text("ALTER TABLE tasks ALTER COLUMN status SET DEFAULT 'todo'")
        )
        connection.execute(
            text("ALTER TABLE tasks ALTER COLUMN priority SET DEFAULT 'medium'")
        )
        connection.execute(
            text("ALTER TABLE tasks ALTER COLUMN category SET DEFAULT 'Execução'")
        )
        for table in ("users", "projects", "tasks"):
            connection.execute(
                text(f"ALTER TABLE {table} ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP")
            )

    inspector = inspect(engine)
    missing_columns = {
        table_name: sorted(
            column.name
            for column in model_table.columns
            if column.name
            not in {
                column_info["name"]
                for column_info in inspector.get_columns(table_name)
            }
        )
        for table_name, model_table in Base.metadata.tables.items()
    }
    missing_columns = {
        table_name: columns
        for table_name, columns in missing_columns.items()
        if columns
    }
    if missing_columns:
        details = "; ".join(
            f"{table}: {', '.join(columns)}"
            for table, columns in missing_columns.items()
        )
        raise RuntimeError(
            "Faltam colunas necessárias no esquema PostgreSQL: " + details
        )

    expected_primary_keys = {
        "users": ("id",),
        "projects": ("id",),
        "tasks": ("id",),
        "project_members": ("project_id", "user_id"),
    }
    for table, expected_columns in expected_primary_keys.items():
        primary_key = inspect(engine).get_pk_constraint(table)
        actual_columns = tuple(primary_key.get("constrained_columns") or ())
        if actual_columns != expected_columns:
            raise RuntimeError(
                f"A chave primária de {table} é {actual_columns or 'inexistente'}; "
                f"era esperada {expected_columns}. Corrija-a preservando os dados "
                "antes de iniciar a API."
            )

    _ensure_foreign_key(engine, "projects", "owner_id", "users", "id")
    _ensure_foreign_key(
        engine, "tasks", "project_id", "projects", "id", "CASCADE"
    )
    _ensure_foreign_key(
        engine, "tasks", "assignee_id", "users", "id", "SET NULL"
    )
    _ensure_foreign_key(
        engine, "project_members", "project_id", "projects", "id", "CASCADE"
    )
    _ensure_foreign_key(
        engine, "project_members", "user_id", "users", "id", "CASCADE"
    )

    _ensure_check(
        engine,
        "tasks",
        "ck_tasks_status",
        TASK_STATUSES,
        "status IN ('todo', 'in_progress', 'done', 'blocked')",
    )
    _ensure_check(
        engine,
        "tasks",
        "ck_tasks_priority",
        TASK_PRIORITIES,
        "priority IN ('low', 'medium', 'high')",
    )
    _ensure_check(
        engine,
        "tasks",
        "ck_tasks_category",
        TASK_CATEGORIES,
        "category IN ('Planeamento', 'Pesquisa', 'Conceção', "
        "'Execução', 'Validação', 'Documentação')",
    )
    _ensure_check(
        engine,
        "projects",
        "ck_projects_category",
        PROJECT_CATEGORIES,
        "category IN ('Investigação', 'Desenvolvimento', 'Seminário', "
        "'Estudo de caso', 'Outro')",
    )
    _ensure_check(
        engine,
        "projects",
        "ck_projects_color",
        (),
        "length(color) = 7 AND substr(color, 1, 1) = '#'",
    )
    _ensure_check(
        engine,
        "projects",
        "ck_projects_name_length",
        (),
        "length(trim(name)) BETWEEN 2 AND 160",
    )
    _ensure_check(
        engine,
        "tasks",
        "ck_tasks_title_length",
        (),
        "length(trim(title)) BETWEEN 2 AND 200",
    )
    _ensure_check(
        engine,
        "users",
        "ck_users_name_length",
        (),
        "length(trim(name)) BETWEEN 2 AND 120",
    )
    _ensure_check(
        engine,
        "users",
        "ck_users_email_normalized",
        (),
        "email = lower(trim(email)) AND length(email) > 0",
    )

    _ensure_index(
        engine,
        "uq_users_email_lower",
        "CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))",
        "users",
        unique=True,
    )
    _ensure_index(
        engine,
        "ix_projects_owner_id",
        "CREATE INDEX ix_projects_owner_id ON projects (owner_id)",
        "projects",
        ("owner_id",),
    )
    _ensure_index(
        engine,
        "ix_tasks_project_id",
        "CREATE INDEX ix_tasks_project_id ON tasks (project_id)",
        "tasks",
        ("project_id",),
    )
    _ensure_index(
        engine,
        "ix_tasks_status",
        "CREATE INDEX ix_tasks_status ON tasks (status)",
        "tasks",
        ("status",),
    )
    _ensure_index(
        engine,
        "ix_tasks_priority",
        "CREATE INDEX ix_tasks_priority ON tasks (priority)",
        "tasks",
        ("priority",),
    )
    _ensure_index(
        engine,
        "ix_tasks_assignee_id",
        "CREATE INDEX ix_tasks_assignee_id ON tasks (assignee_id)",
        "tasks",
        ("assignee_id",),
    )
    _ensure_index(
        engine,
        "ix_tasks_deadline",
        "CREATE INDEX ix_tasks_deadline ON tasks (deadline)",
        "tasks",
        ("deadline",),
    )
    _ensure_index(
        engine,
        "ix_project_members_user_id",
        "CREATE INDEX ix_project_members_user_id ON project_members (user_id)",
        "project_members",
        ("user_id",),
    )
