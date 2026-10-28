import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_app
from app.main import app
from app.migrations import upgrade_legacy_postgres_schema
from app.models import (
    Attachment,
    Comment,
    ModelStage,
    Notification,
    Project,
    ProjectMember,
    ProjectModel,
    ProjectType,
    Stage,
    Task,
    TaskStage,
    Team,
    TeamMember,
    User,
)
from db.session import Base, get_db


# A suite de testes monta uma base SQLite em memoria, sobrepoe o `get_db` da
# app e valida fluxo de autenticacao, projetos, tarefas e integracoes de migracao.
class TaskFlowApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(cls.engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.original_app_engine = main_app.engine
        main_app.engine = cls.engine

        def override_get_db():
            with cls.session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        main_app.engine = cls.original_app_engine
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def register(self, name: str, email: str) -> tuple[str, int]:
        response = self.client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": "palavra-passe-segura"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        return body["access_token"], body["user"]["id"]

# Este teste cobre o fluxo principal: registro, criacao de projeto, atribuicao,
# filtros e atualizacao de membros/estado.
    def test_authenticated_project_task_and_team_flow(self) -> None:
        token, owner_id = self.register("Ramalho", "ramalho@example.pt")
        headers = {"Authorization": f"Bearer {token}"}

        project_response = self.client.post(
            "/api/projects",
            headers=headers,
            json={
                "name": "Projeto de investigação",
                "description": "Estudo académico",
                "category": "Investigação",
                "color": "#7165e8",
            },
        )
        self.assertEqual(project_response.status_code, 201, project_response.text)
        project = project_response.json()
        self.assertEqual(project["task_count"], 0)

        task_response = self.client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers,
            json={"title": "Rever bibliografia", "priority": "high", "deadline": "2026-11-01"},
        )
        self.assertEqual(task_response.status_code, 201, task_response.text)
        task = task_response.json()
        self.assertEqual(task["assignee_id"], owner_id)

        status_response = self.client.patch(
            f"/api/projects/{project['id']}/tasks/{task['id']}",
            headers=headers,
            json={"status": "done"},
        )
        self.assertEqual(status_response.status_code, 200, status_response.text)
        self.assertEqual(status_response.json()["status"], "done")

        refreshed_project = self.client.get("/api/projects", headers=headers).json()[0]
        self.assertEqual(refreshed_project["completed_count"], 1)

        archive_response = self.client.patch(
            f"/api/projects/{project['id']}",
            headers=headers,
            json={"archived": True},
        )
        self.assertEqual(archive_response.status_code, 200)
        self.assertTrue(archive_response.json()["archived"])
        self.assertEqual(self.client.get("/api/projects", headers=headers).json(), [])
        archived_projects = self.client.get(
            "/api/projects",
            headers=headers,
            params={"archived": "true"},
        )
        self.assertEqual(archived_projects.status_code, 200)
        self.assertEqual(archived_projects.json()[0]["id"], project["id"])
        restore_response = self.client.patch(
            f"/api/projects/{project['id']}",
            headers=headers,
            json={"archived": False},
        )
        self.assertEqual(restore_response.status_code, 200)
        self.assertFalse(restore_response.json()["archived"])

        teammate_token, teammate_id = self.register("Ana", "ana@example.pt")
        invite_response = self.client.post(
            f"/api/projects/{project['id']}/members",
            headers=headers,
            json={"email": "ana@example.pt"},
        )
        self.assertEqual(invite_response.status_code, 200, invite_response.text)
        self.assertEqual(len(invite_response.json()), 2)

        teammate_headers = {"Authorization": f"Bearer {teammate_token}"}
        teammate_projects = self.client.get("/api/projects", headers=teammate_headers)
        self.assertEqual(teammate_projects.status_code, 200)
        self.assertEqual(teammate_projects.json()[0]["id"], project["id"])

        assigned_task = self.client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers,
            json={"title": "Preparar apresentação", "assignee_id": teammate_id},
        )
        self.assertEqual(assigned_task.status_code, 201, assigned_task.text)
        teammate_notifications = self.client.get(
            "/api/notifications", headers=teammate_headers
        )
        self.assertEqual(teammate_notifications.status_code, 200)
        self.assertEqual(
            {
                notification["notification_type"]
                for notification in teammate_notifications.json()
            },
            {"project_invitation", "task_assigned"},
        )
        filtered = self.client.get(
            f"/api/projects/{project['id']}/tasks",
            headers=teammate_headers,
            params={"assignee_id": teammate_id, "status": "todo"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([item["title"] for item in filtered.json()], ["Preparar apresentação"])

        with self.session_factory() as session:
            session.delete(session.get(User, teammate_id))
            session.commit()
            preserved_task = session.get(Task, assigned_task.json()["id"])
            self.assertIsNone(preserved_task.assignee_id)

        invalid_filter = self.client.get(
            f"/api/projects/{project['id']}/tasks",
            headers=headers,
            params={"status": "invalido"},
        )
        self.assertEqual(invalid_filter.status_code, 422)

    def test_database_constraints_and_cascades(self) -> None:
        token, owner_id = self.register("Diana", "diana@example.pt")
        headers = {"Authorization": f"Bearer {token}"}
        project = self.client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Integridade relacional"},
        ).json()
        task = self.client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers,
            json={"title": "Validar integridade"},
        ).json()

        with self.session_factory() as session:
            session.add(
                User(
                    name="Duplicada",
                    email="diana@example.pt",
                    password_hash="unused",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

            stored_task = session.get(Task, task["id"])
            self.assertEqual(stored_task.project_id, project["id"])
            self.assertEqual(stored_task.assignee_id, owner_id)
            stored_task.status = "not-a-valid-status"
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

            stored_project = session.get(Project, project["id"])
            session.delete(stored_project)
            session.commit()
            self.assertIsNone(session.get(Task, task["id"]))
            self.assertIsNone(session.get(Project, project["id"]))

    def test_all_domain_entities_and_relationships(self) -> None:
        with self.session_factory() as session:
            owner = User(
                name="Entidades",
                email="entidades@example.pt",
                password_hash="unused",
                user_type="student",
                course="Engenharia",
                avatar_url="https://example.pt/avatar.png",
            )
            project = Project(
                name="Modelo relacional",
                owner=owner,
                leader=owner,
                status="active",
            )
            project_type = ProjectType(name="Tipo de investigação")
            project.project_type = project_type
            member = User(
                name="Membro",
                email="membro@example.pt",
                password_hash="unused",
            )
            project.members.append(member)
            project.team = Team(
                name="Equipa do projeto",
                memberships=[
                    TeamMember(user=owner, role="leader"),
                    TeamMember(user=member, role="member"),
                ],
            )
            project_model = ProjectModel(
                name="Modelo académico",
                project_type=project_type,
                stage_structure=[{"name": "Planeamento", "order": 1}],
            )
            model_stage = ModelStage(
                name="Planeamento", order=1, project_model=project_model
            )
            stage = Stage(name="Planeamento", order=1, project=project)
            task = Task(
                title="Validar relações",
                project=project,
                stage=stage,
                assignee=member,
                stages=[model_stage],
            )
            comment = Comment(content="Comentário", task=task, user=member)
            attachment = Attachment(
                file_name="plano.pdf",
                url="https://example.pt/plano.pdf",
                file_type="application/pdf",
                size_bytes=512,
                task=task,
                uploaded_by=member,
            )
            notification = Notification(
                title="Nova tarefa",
                message="Foi atribuída uma tarefa.",
                notification_type="task_assigned",
                user=member,
            )
            session.add_all([project, comment, attachment, notification])
            session.commit()

            session.refresh(project)
            session.refresh(task)
            self.assertEqual(project.members[0].email, "membro@example.pt")
            self.assertEqual(project.memberships[0].role, "member")
            self.assertEqual(project.team.memberships[0].role, "leader")
            self.assertEqual(project.team.members[1].email, "membro@example.pt")
            self.assertEqual(project.project_type.name, "Tipo de investigação")
            self.assertEqual(project_type.models[0].stage_structure[0]["name"], "Planeamento")
            self.assertEqual(task.stage.name, "Planeamento")
            self.assertEqual(task.stages[0].name, "Planeamento")
            self.assertEqual(task.comments[0].user.email, "membro@example.pt")
            self.assertEqual(task.attachments[0].size_bytes, 512)
            self.assertEqual(member.notifications[0].notification_type, "task_assigned")
            membership_id = project.memberships[0].id
            task_id, comment_id, attachment_id = task.id, comment.id, attachment.id
            notification_id = notification.id
            task_stage_id = task.stage_links[0].id
            team_id = project.team.id

            session.delete(stage)
            session.commit()
            self.assertIsNone(task.stage_id)

            session.delete(project)
            session.commit()
            self.assertIsNone(session.get(ProjectMember, membership_id))
            self.assertIsNone(session.get(Task, task_id))
            self.assertIsNone(session.get(Comment, comment_id))
            self.assertIsNone(session.get(Attachment, attachment_id))
            self.assertIsNone(session.get(TaskStage, task_stage_id))
            self.assertIsNone(session.get(Team, team_id))
            session.delete(member)
            session.commit()
            self.assertIsNone(session.get(Notification, notification_id))

    def test_task_comments_and_private_notifications(self) -> None:
        token, owner_id = self.register("Comentários", "comentarios@example.pt")
        headers = {"Authorization": f"Bearer {token}"}
        project_response = self.client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Projeto de comentários"},
        )
        self.assertEqual(project_response.status_code, 201, project_response.text)
        project = project_response.json()
        task = self.client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers,
            json={"title": "Discutir resultado"},
        ).json()

        comment_response = self.client.post(
            f"/api/projects/{project['id']}/tasks/{task['id']}/comments",
            headers=headers,
            json={"content": "  Vamos rever os resultados.  "},
        )
        self.assertEqual(comment_response.status_code, 201, comment_response.text)
        self.assertEqual(comment_response.json()["content"], "Vamos rever os resultados.")
        listed_comments = self.client.get(
            f"/api/projects/{project['id']}/tasks/{task['id']}/comments",
            headers=headers,
        )
        self.assertEqual(len(listed_comments.json()), 1)
        with self.session_factory() as session:
            session.add(
                Attachment(
                    file_name="resultados.pdf",
                    url="https://example.pt/resultados.pdf",
                    file_type="application/pdf",
                    size_bytes=1024,
                    task_id=task["id"],
                    uploaded_by_id=owner_id,
                )
            )
            session.commit()
        project_attachments = self.client.get(
            f"/api/projects/{project['id']}/attachments", headers=headers
        )
        self.assertEqual(project_attachments.status_code, 200)
        self.assertEqual(project_attachments.json()[0]["file_name"], "resultados.pdf")

        with self.session_factory() as session:
            notification = Notification(
                title="Tarefa atualizada",
                message="A tarefa foi atualizada.",
                notification_type="task_updated",
                user_id=owner_id,
            )
            session.add(notification)
            session.commit()
            notification_id = notification.id

        notification_response = self.client.get("/api/notifications", headers=headers)
        self.assertEqual(notification_response.status_code, 200)
        self.assertFalse(notification_response.json()[0]["is_read"])
        marked_read = self.client.patch(
            f"/api/notifications/{notification_id}/read", headers=headers
        )
        self.assertEqual(marked_read.status_code, 200)
        self.assertTrue(marked_read.json()["is_read"])

    def test_task_attachment_upload_and_download(self) -> None:
        token, _owner_id = self.register("Anexos", "anexos@example.pt")
        headers = {"Authorization": f"Bearer {token}"}
        project = self.client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Projeto com anexos"},
        ).json()
        task = self.client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers,
            json={"title": "Rever documento"},
        ).json()
        upload_path = f"/api/projects/{project['id']}/tasks/{task['id']}/attachments"
        content = b"Conteudo de teste do anexo."

        with TemporaryDirectory() as upload_dir, patch(
            "api.routes.tasks.UPLOAD_DIR", Path(upload_dir)
        ):
            uploaded = self.client.post(
                upload_path,
                headers=headers,
                files={"file": ("resumo.txt", content, "text/plain")},
            )
            self.assertEqual(uploaded.status_code, 201, uploaded.text)
            attachment = uploaded.json()
            self.assertEqual(attachment["file_name"], "resumo.txt")
            self.assertEqual(attachment["size_bytes"], len(content))
            self.assertEqual(attachment["task_id"], task["id"])

            downloaded = self.client.get(attachment["url"], headers=headers)
            self.assertEqual(downloaded.status_code, 200, downloaded.text)
            self.assertEqual(downloaded.content, content)
            self.assertIn("attachment", downloaded.headers["content-disposition"])

            unauthenticated = self.client.get(attachment["url"])
            self.assertEqual(unauthenticated.status_code, 401)

    def test_legacy_sqlite_schema_is_upgraded_without_losing_members(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        try:
            with engine.begin() as connection:
                connection.execute(text("PRAGMA foreign_keys=ON"))
                connection.execute(
                    text(
                        "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(120) "
                        "NOT NULL, email VARCHAR(255) NOT NULL, password_hash VARCHAR(255) "
                        "NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE TABLE projects (id INTEGER PRIMARY KEY, name VARCHAR(160) "
                        "NOT NULL, description TEXT NOT NULL DEFAULT '', category VARCHAR(40) "
                        "NOT NULL DEFAULT 'Desenvolvimento', color VARCHAR(20) NOT NULL "
                        "DEFAULT '#6c63ff', archived BOOLEAN NOT NULL DEFAULT 0, owner_id "
                        "INTEGER NOT NULL REFERENCES users(id), created_at DATETIME "
                        "DEFAULT CURRENT_TIMESTAMP)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title VARCHAR(200) "
                        "NOT NULL, description TEXT NOT NULL DEFAULT '', status VARCHAR(20) "
                        "NOT NULL DEFAULT 'todo', priority VARCHAR(20) NOT NULL DEFAULT "
                        "'medium', category VARCHAR(40) NOT NULL DEFAULT 'Execução', "
                        "deadline DATE, project_id INTEGER NOT NULL REFERENCES projects(id) "
                        "ON DELETE CASCADE, assignee_id INTEGER REFERENCES users(id) "
                        "ON DELETE SET NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE TABLE project_members (project_id INTEGER NOT NULL "
                        "REFERENCES projects(id) ON DELETE CASCADE, user_id INTEGER NOT NULL "
                        "REFERENCES users(id) ON DELETE CASCADE, PRIMARY KEY (project_id, user_id))"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO users (id, name, email, password_hash) VALUES "
                        "(1, 'Criador', 'criador@example.pt', 'hash'), "
                        "(2, 'Membro', 'membro@example.pt', 'hash')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO projects (id, name, owner_id) "
                        "VALUES (1, 'Projeto antigo', 1)"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO project_members (project_id, user_id) VALUES (1, 2)"
                    )
                )
            Base.metadata.create_all(bind=engine)
            upgrade_legacy_postgres_schema(engine)

            member_table = inspect(engine)
            self.assertEqual(
                member_table.get_pk_constraint("project_members")["constrained_columns"],
                ["id"],
            )
            with engine.connect() as connection:
                self.assertEqual(
                    connection.execute(
                        text("SELECT project_id, user_id, role FROM project_members")
                    ).one(),
                    (1, 2, "member"),
                )
                self.assertEqual(
                    connection.execute(
                        text("SELECT name, project_id FROM teams")
                    ).one(),
                    ("Projeto antigo", 1),
                )
                self.assertEqual(
                    connection.execute(
                        text(
                            "SELECT project_type_id FROM projects WHERE id = 1"
                        )
                    ).scalar_one(),
                    connection.execute(
                        text(
                            "SELECT id FROM project_types WHERE name = 'Desenvolvimento'"
                        )
                    ).scalar_one(),
                )
                self.assertEqual(
                    connection.execute(
                        text(
                            "SELECT role FROM team_members "
                            "WHERE user_id = 2"
                        )
                    ).scalar_one(),
                    "member",
                )
                task_foreign_keys = member_table.get_foreign_keys("tasks")
                self.assertTrue(
                    any(
                        fk["constrained_columns"] == ["stage_id"]
                        and fk["referred_table"] == "stages"
                        for fk in task_foreign_keys
                    )
                )
        finally:
            engine.dispose()

    def test_health_checks_database(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"api": "online", "database": "online"})

    def test_dashboard_stats_aggregate_only_accessible_tasks(self) -> None:
        token, _owner_id = self.register("Dashboard", "dashboard@example.pt")
        headers = {"Authorization": f"Bearer {token}"}
        project = self.client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Projeto dashboard"},
        ).json()

        for payload in (
            {"title": "Concluída", "status": "done", "priority": "high"},
            {
                "title": "Em atraso",
                "status": "todo",
                "priority": "low",
                "deadline": "2000-01-01",
            },
            {
                "title": "Próxima",
                "status": "in_progress",
                "priority": "medium",
                "deadline": date.today().isoformat(),
            },
        ):
            response = self.client.post(
                f"/api/projects/{project['id']}/tasks", headers=headers, json=payload
            )
            self.assertEqual(response.status_code, 201, response.text)

        other_token, _ = self.register("Outro", "outro-dashboard@example.pt")
        other_headers = {"Authorization": f"Bearer {other_token}"}
        other_project = self.client.post(
            "/api/projects", headers=other_headers, json={"name": "Projeto privado"}
        ).json()
        self.client.post(
            f"/api/projects/{other_project['id']}/tasks",
            headers=other_headers,
            json={"title": "Tarefa privada", "status": "blocked"},
        )

        response = self.client.get("/api/dashboard/stats", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        stats = response.json()
        self.assertEqual(stats["projects_total"], 1)
        self.assertEqual(stats["tasks_total"], 3)
        self.assertEqual(stats["tasks_done"], 1)
        self.assertEqual(stats["tasks_overdue"], 1)
        self.assertEqual(stats["completion_rate"], 33)
        self.assertEqual(
            stats["tasks_by_status"],
            [
                {"status": "todo", "count": 1},
                {"status": "in_progress", "count": 1},
                {"status": "done", "count": 1},
                {"status": "blocked", "count": 0},
            ],
        )
        self.assertEqual(len(stats["upcoming_deadlines"]), 1)
        self.assertEqual(stats["upcoming_deadlines"][0]["title"], "Próxima")

    def test_private_routes_require_authentication(self) -> None:
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 401)

    def test_auth_preflight_allows_local_frontend_port(self) -> None:
        response = self.client.options(
            "/api/auth/register",
            headers={
                "Origin": "http://localhost:3210",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:3210",
        )
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")

    def test_names_with_only_whitespace_are_rejected(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "name": "   ",
                "email": "whitespace@example.pt",
                "password": "palavra-passe-segura",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
