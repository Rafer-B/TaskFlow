from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_accessible_project, get_current_user
from app.models import Project, Task, User
from app.schemas import ProjectCreate, ProjectMemberAdd, ProjectPublic, ProjectUpdate, UserPublic
from db.session import get_db

router = APIRouter(prefix="/api/projects", tags=["Projetos"])


def project_response(project: Project) -> ProjectPublic:
    total = len(project.tasks)
    completed = sum(task.status == "done" for task in project.tasks)
    return ProjectPublic(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category,
        color=project.color,
        archived=project.archived,
        owner_id=project.owner_id,
        created_at=project.created_at,
        members=project.members,
        task_count=total,
        completed_count=completed,
    )


@router.get("", response_model=list[ProjectPublic])
def list_projects(
    archived: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectPublic]:
    projects = db.scalars(
        select(Project)
        .where(
            Project.archived == archived,
            (Project.owner_id == user.id) | Project.members.any(User.id == user.id),
        )
        .options(selectinload(Project.members), selectinload(Project.tasks))
        .order_by(Project.created_at.desc())
    ).all()
    return [project_response(project) for project in projects]


@router.post("", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectPublic:
    project = Project(**data.model_dump(), owner=user)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_response(project)


@router.patch("/{project_id}", response_model=ProjectPublic)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectPublic:
    project = get_accessible_project(project_id, user, db)
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Só o responsável pode editar o projeto.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = get_accessible_project(project_id, user, db)
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Só o responsável pode eliminar o projeto.")
    db.delete(project)
    db.commit()


@router.post("/{project_id}/members", response_model=list[UserPublic])
def add_project_member(
    project_id: int,
    data: ProjectMemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserPublic]:
    project = get_accessible_project(project_id, user, db)
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Só o responsável pode convidar membros.")
    member = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if member is None:
        raise HTTPException(status_code=404, detail="Não existe uma conta com esse email.")
    if member.id != project.owner_id and member not in project.members:
        project.members.append(member)
        db.commit()
    return [UserPublic.model_validate(project.owner), *[
        UserPublic.model_validate(item) for item in project.members
    ]]


@router.get("/{project_id}/members", response_model=list[UserPublic])
def list_project_members(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserPublic]:
    project = get_accessible_project(project_id, user, db)
    members = [project.owner, *project.members]
    unique_members = {member.id: UserPublic.model_validate(member) for member in members}
    return list(unique_members.values())
