from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.dependencies import get_current_user
from app.models import Project, Task, User
from db.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _accessible_tasks(db: Session, user: User) -> list[Task]:
    """Obtém as tarefas dos projetos aos quais o utilizador tem acesso."""
    return list(
        db.scalars(
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .where(
                (Project.owner_id == user.id)
                | Project.members.any(User.id == user.id)
            )
            .options(joinedload(Task.assignee), joinedload(Task.project))
            .order_by(Task.created_at.desc())
        ).unique()
    )


@router.get("/stats")
def dashboard_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Devolve métricas agregadas para o dashboard do utilizador autenticado."""
    today = date.today()
    projects = list(
        db.scalars(
            select(Project)
            .where(
                (Project.owner_id == user.id)
                | Project.members.any(User.id == user.id)
            )
            .options(selectinload(Project.tasks))
            .order_by(Project.created_at.desc())
        ).unique()
    )
    tasks = _accessible_tasks(db, user)

    task_counts: dict[str, int] = {
        "todo": 0,
        "in_progress": 0,
        "done": 0,
        "blocked": 0,
    }
    tasks_by_priority: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    overdue_tasks: list[Task] = []
    upcoming: list[Task] = []

    for task in tasks:
        task_counts[task.status] = task_counts.get(task.status, 0) + 1
        tasks_by_priority[task.priority] = tasks_by_priority.get(task.priority, 0) + 1

        if task.status == "done" or task.deadline is None:
            continue
        if task.deadline < today:
            overdue_tasks.append(task)
        elif task.deadline <= today + timedelta(days=7):
            upcoming.append(task)

    tasks_total = len(tasks)
    tasks_done = task_counts["done"]
    upcoming.sort(key=lambda task: task.deadline or date.max)

    projects_summary = []
    for project in projects[:5]:
        total = len(project.tasks)
        completed = sum(task.status == "done" for task in project.tasks)
        projects_summary.append(
            {
                "id": project.id,
                "name": project.name,
                "color": project.color,
                "task_count": total,
                "completed_count": completed,
                "progress": int(round((completed / total) * 100)) if total else 0,
            }
        )

    return {
        "projects_total": len(projects),
        "projects_active": sum(not project.archived for project in projects),
        "projects_archived": sum(project.archived for project in projects),
        "tasks_total": tasks_total,
        "tasks_done": tasks_done,
        "tasks_in_progress": task_counts["in_progress"],
        "tasks_todo": task_counts["todo"],
        "tasks_blocked": task_counts["blocked"],
        "tasks_overdue": len(overdue_tasks),
        "completion_rate": int(round((tasks_done / tasks_total) * 100))
        if tasks_total
        else 0,
        "tasks_by_status": [
            {"status": status, "count": task_counts[status]}
            for status in ("todo", "in_progress", "done", "blocked")
        ],
        "tasks_by_priority": [
            {"priority": priority, "count": tasks_by_priority[priority]}
            for priority in ("low", "medium", "high")
        ],
        "recent_tasks": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "project_name": task.project.name,
                "project_color": task.project.color,
                "assignee_name": task.assignee.name if task.assignee else None,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks[:5]
        ],
        "upcoming_deadlines": [
            {
                "id": task.id,
                "title": task.title,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "project_name": task.project.name,
                "project_color": task.project.color,
                "status": task.status,
                "days_left": (task.deadline - today).days if task.deadline else None,
            }
            for task in upcoming[:5]
        ],
        "projects_summary": projects_summary,
    }