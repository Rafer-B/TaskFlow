from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_accessible_project, get_current_user
from app.models import Project, Task, User
from app.schemas import TaskCreate, TaskPriority, TaskPublic, TaskStatus, TaskUpdate
from db.session import get_db

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["Tarefas"])


def check_assignee(
    project: Project, assignee_id: int | None, db: Session
) -> User | None:
    if assignee_id is None:
        return None
    assignee = db.scalar(select(User).where(User.id == assignee_id))
    if assignee is None or (assignee.id != project.owner_id and assignee not in project.members):
        raise HTTPException(status_code=422, detail="O responsável não pertence a este projeto.")
    return assignee


@router.get("", response_model=list[TaskPublic])
def list_tasks(
    project_id: int,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Task]:
    get_accessible_project(project_id, user, db)
    query = select(Task).where(Task.project_id == project_id).options(joinedload(Task.assignee))
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    if deadline_from:
        query = query.where(Task.deadline >= deadline_from)
    if deadline_to:
        query = query.where(Task.deadline <= deadline_to)
    return list(
        db.scalars(
            query.order_by(Task.deadline.asc().nullslast(), Task.created_at.desc())
        ).all()
    )


@router.post("", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: int,
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    project = get_accessible_project(project_id, user, db)
    assignee_id = data.assignee_id if data.assignee_id is not None else user.id
    check_assignee(project, assignee_id, db)
    task = Task(**data.model_dump(exclude={"assignee_id"}), project=project, assignee_id=assignee_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    saved_task = db.scalar(
        select(Task).where(Task.id == task.id).options(joinedload(Task.assignee))
    )
    if saved_task is None:
        raise HTTPException(status_code=500, detail="Não foi possível carregar a tarefa criada.")
    return saved_task


@router.patch("/{task_id}", response_model=TaskPublic)
def update_task(
    project_id: int,
    task_id: int,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    project = get_accessible_project(project_id, user, db)
    task = db.scalar(
        select(Task)
        .where(Task.id == task_id, Task.project_id == project.id)
        .options(joinedload(Task.assignee))
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    changes = data.model_dump(exclude_unset=True)
    if "assignee_id" in changes:
        check_assignee(project, changes["assignee_id"], db)
    for key, value in changes.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    saved_task = db.scalar(
        select(Task).where(Task.id == task.id).options(joinedload(Task.assignee))
    )
    if saved_task is None:
        raise HTTPException(status_code=500, detail="Não foi possível carregar a tarefa atualizada.")
    return saved_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    project_id: int,
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    get_accessible_project(project_id, user, db)
    task = db.scalar(select(Task).where(Task.id == task_id, Task.project_id == project_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
