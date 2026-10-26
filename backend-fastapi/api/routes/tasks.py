import mimetypes
import os
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_accessible_project, get_current_user
from app.models import Attachment, Comment, Notification, Project, Task, User
from app.schemas import (
    AttachmentPublic,
    CommentCreate,
    CommentPublic,
    TaskCreate,
    TaskPriority,
    TaskPublic,
    TaskStatus,
    TaskUpdate,
)
from db.session import get_db

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["Tarefas"])
UPLOAD_DIR = Path(
    os.getenv("TASKFLOW_UPLOAD_DIR", str(Path(__file__).resolve().parents[2] / "uploads"))
)
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024

# Esta rota aninhada usa o `project_id` como limite de escopo e evita que uma tarefa
# de outro projeto seja consultada ou editada por acidente.


@router.post(
    "/{task_id}/attachments",
    response_model=AttachmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_task_attachment(
    project_id: int,
    task_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Attachment:
    project = get_accessible_project(project_id, user, db)
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.project_id == project.id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    file_name = (file.filename or "").replace("\\", "/").split("/")[-1]
    file_name = "".join(
        character for character in file_name if character.isprintable()
    ).strip()
    if not file_name:
        raise HTTPException(status_code=422, detail="O ficheiro tem um nome inválido.")
    file_name = file_name[:255]

    storage_key = uuid4().hex
    file_path = UPLOAD_DIR / storage_key
    size_bytes = 0
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with file_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > MAX_ATTACHMENT_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="O ficheiro excede o limite de 10 MB.",
                    )
                destination.write(chunk)
        if size_bytes == 0:
            raise HTTPException(status_code=422, detail="Não é possível anexar um ficheiro vazio.")

        attachment = Attachment(
            file_name=file_name,
            url=f"/api/projects/{project.id}/tasks/{task.id}/attachments/{storage_key}",
            file_type=mimetypes.guess_type(file_name)[0] or "application/octet-stream",
            size_bytes=size_bytes,
            task=task,
            uploaded_by=user,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        return attachment
    except (OSError, SQLAlchemyError):
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.get("/{task_id}/attachments/{storage_key}")
def download_task_attachment(
    project_id: int,
    task_id: int,
    storage_key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    project = get_accessible_project(project_id, user, db)
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.project_id == project.id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    if len(storage_key) != 32 or any(
        character not in "0123456789abcdef" for character in storage_key
    ):
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.task_id == task.id,
            Attachment.url
            == f"/api/projects/{project.id}/tasks/{task.id}/attachments/{storage_key}",
        )
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")

    file_path = UPLOAD_DIR / storage_key
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Ficheiro do anexo não encontrado.")
    return FileResponse(
        file_path,
        media_type=attachment.file_type,
        filename=attachment.file_name,
        content_disposition_type="attachment",
    )


@router.get("/{task_id}/comments", response_model=list[CommentPublic])
def list_comments(
    project_id: int,
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Comment]:
    project = get_accessible_project(project_id, user, db)
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.project_id == project.id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return list(
        db.scalars(
            select(Comment)
            .where(Comment.task_id == task.id)
            .options(joinedload(Comment.user))
            .order_by(Comment.created_at.asc())
        ).all()
    )


@router.post(
    "/{task_id}/comments",
    response_model=CommentPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    project_id: int,
    task_id: int,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Comment:
    project = get_accessible_project(project_id, user, db)
    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.project_id == project.id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    comment = Comment(content=data.content, task=task, user=user)
    db.add(comment)
    if task.assignee_id is not None and task.assignee_id != user.id:
        db.add(
            Notification(
                user_id=task.assignee_id,
                title="Novo comentário numa tarefa",
                message=f"{user.name} comentou «{task.title}».",
                notification_type="comment",
            )
        )
    db.commit()
    db.refresh(comment)
    return comment


# A validacao do responsavel garante que o utilizador atribuido faz parte do
# mesmo projeto ou e o dono, evitando tarefas orfas ou acessos indevidos.
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


# A criacao de tarefas usa o assignee do payload ou o proprio dono do projeto
# como fallback, mantendo coercoes de regras de negocio em um unico lugar.
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
    if assignee_id is not None and assignee_id != user.id:
        db.add(
            Notification(
                user_id=assignee_id,
                title="Nova tarefa atribuída",
                message=f"A tarefa «{task.title}» foi atribuída a ti.",
                notification_type="task_assigned",
            )
        )
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
    previous_assignee_id = task.assignee_id
    if "assignee_id" in changes:
        check_assignee(project, changes["assignee_id"], db)
    for key, value in changes.items():
        setattr(task, key, value)
    if task.assignee_id is not None and task.assignee_id != previous_assignee_id:
        db.add(
            Notification(
                user_id=task.assignee_id,
                title="Tarefa atribuída a ti",
                message=f"A tarefa «{task.title}» foi atribuída a ti.",
                notification_type="task_assigned",
            )
        )
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
