from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import get_db
from app.models import Project, User
from app.security import get_user_id_from_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = get_user_id_from_token(credentials.credentials)
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Utilizador não encontrado.")
    return user


def get_accessible_project(project_id: int, user: User, db: Session) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            (Project.owner_id == user.id) | Project.members.any(User.id == user.id),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return project
