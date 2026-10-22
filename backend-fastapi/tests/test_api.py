import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_app
from app.main import app
from app.models import Project, Task, User
from db.session import Base, get_db


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

    def test_health_checks_database(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"api": "online", "database": "online"})

    def test_private_routes_require_authentication(self) -> None:
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 401)

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
