from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, joinedload

from app.dependencies import get_current_user
from app.models import Project, Task, User
from db.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _task_counts(db: Session, user: User) -> dict[str, int]:
    counts: dict[str, int] = {"todo": 0, "in_progress": 0, "done": 0, "blocked": 0}
    tasks = db.scalars(
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(

@router.get("/stats")
def dashboard_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devolve métricas agregadas para o dashboard do utilizador autenticado."""
    today = date.today()
    overdue_threshold = datetime.combine(today, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )

    # Projetos acessíveis
    projects = db.scalars(
        select(Project)
        .where(
            (Project.owner_id == user.id) | Project.members.any(User.id == user.id)
        )
        .options(selectinload(Project.tasks))
        .order_by(Project.created_at.desc())
    ).all()

    projects_total = len(projects)
    projects_active = sum(1 for p in projects if not p.archived)
    projects_archived = sum(1 for p in projects if p.archived)

    # Tarefas
    task_counts = _task_counts(db, user)
    tasks_total = sum(task_counts.values())
    tasks_done = task_counts.get("done", 0)
    tasks_in_progress = task_counts.get("in_progress", 0)
    tasks_todo = task_counts.get("todo", 0)
    tasks_blocked = task_counts.get("blocked", 0)

    # Tarefas em atraso (prazo passado e ainda não concluídas)
    tasks_overdue = 0
    for project in projects:
        for task in project.tasks:
            if (
                task.status != "done"
                and task.deadline is not None
                and datetime.fromisoformat(task.deadline).date() < today
            ):
                tasks_overdue += 1

    # Taxa de conclusão
    completion_rate = int(round((tasks_done / tasks_total) * 100)) if tasks_total else 0

    # Tarefas por prioridade
    tasks_by_priority: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    for project in projects:
        for task in project.tasks:
            tasks_by_priority[task.priority] = (
                tasks_by_priority.get(task.priority, 0) + 1
            )

    # Tarefas recentes (últimas 5 criadas)
    all_tasks = []
    for project in projects:
        for task in project.tasks:
            all_tasks.append(task)
    all_tasks.sort(key=lambda t: t.created_at, reverse=True)
    recent_tasks = [
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
        for task in all_tasks[:5]
    ]

    # Prazos próximos (próximos 7 dias, não concluídos)
    upcoming = []
    for project in projects:
        for task in project.tasks:
            if task.status != "done" and task.deadline is not None:
                deadline_date = datetime.fromisoformat(task.deadline).date()
                if today <= deadline_date <= today + timedelta(days=7):
                    upcoming.append(
                        {
                            "id": task.id,
                            "title": task.title,
                            "deadline": task.deadline,
                            "project_name": task.project.name,
                            "project_color": task.project.color,
                            "status": task.status,
                            "days_left": (deadline_date - today).days,
                        }
                    )
    upcoming.sort(key=lambda x: x["deadline"])
    upcoming_deadlines = upcoming[:5]

    # Resumo de projetos com progresso
    projects_summary = []
    for project in projects[:5]:
        total = len(project.tasks)
        completed = sum(1 for t in project.tasks if t.status == "done")
        progress = int(round((completed / total) * 100)) if total else 0
        projects_summary.append(
            {
                "id": project.id,
                "name": project.name,
                "color": project.color,
                "task_count": total,
                "completed_count": completed,
                "progress": progress,
            }
        )

    return {
        "projects_total": projects_total,
        "projects_active": projects_active,
        "projects_archived": projects_archived,
        "tasks_total": tasks_total,
        "tasks_done": tasks_done,
        "tasks_in_progress": tasks_in_progress,
        "tasks_todo": tasks_todo,
        "tasks_blocked": tasks_blocked,
        "tasks_overdue": tasks_overdue,
        "completion_rate": completion_rate,
        "tasks_by_status": [
            {"status": "todo", "count": task_counts.get("todo", 0)},
            {"status": "in_progress", "count": task_counts.get("in_progress", 0)},
            {"status": "done", "count": task_counts.get("done", 0)},
            {"status": "blocked", "count": task_counts.get("blocked", 0)},
        ],
        "tasks_by_priority": [
            {"priority": "low", "count": tasks_by_priority.get("low", 0)},
            {"priority": "medium", "count": tasks_by_priority.get("medium", 0)},
            {"priority": "high", "count": tasks_by_priority.get("high", 0)},
        ],
        "recent_tasks": recent_tasks,
        "upcoming_deadlines": upcoming_deadlines,
        "projects_summary": projects_summary,
    }
            (Project.owner_id == user.id) | Project.members.any(User.id == user.id)
        )
        .options(joinedload(Task.assignee), joinedload(Task.project))
    ).all()
    for task in tasks:
        counts[task.status] = counts.get(task.status, 0) + 1
    return counts