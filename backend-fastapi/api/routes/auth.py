from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.models import User
from app.schemas import AuthResponse, UserCreate, UserLogin, UserPublic
from app.security import create_access_token, hash_password, verify_password
from db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)) -> AuthResponse:
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Este email já está registado.")
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Este email já está registado.") from error
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(user.id), user=user)


# O login compara email normalizado e hash do password para garantir que a
# autenticacao requer a mesma regra de hashing usada no registo.
@router.post("/login", response_model=AuthResponse)
def login(data: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou palavra-passe incorretos.",
        )
    return AuthResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> User:
    return user
