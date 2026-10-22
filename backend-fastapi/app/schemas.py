from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

TaskStatus = Literal["todo", "in_progress", "done", "blocked"]
TaskPriority = Literal["low", "medium", "high"]
ProjectCategory = Literal[
    "Investigação", "Desenvolvimento", "Seminário", "Estudo de caso", "Outro"
]
TaskCategory = Literal[
    "Planeamento", "Pesquisa", "Conceção", "Execução", "Validação", "Documentação"
]


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("O nome deve ter pelo menos 2 caracteres.")
        return normalized


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=4000)
    category: ProjectCategory = "Desenvolvimento"
    color: str = Field(default="#6c63ff", pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("O nome do projeto deve ter pelo menos 2 caracteres.")
        return normalized


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    category: ProjectCategory | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    archived: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("O nome do projeto deve ter pelo menos 2 caracteres.")
        return normalized


class ProjectMemberAdd(BaseModel):
    email: EmailStr


class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    category: str
    color: str
    archived: bool
    owner_id: int
    created_at: datetime
    members: list[UserPublic]
    task_count: int = 0
    completed_count: int = 0


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    category: TaskCategory = "Execução"
    deadline: date | None = None
    assignee_id: int | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("O título deve ter pelo menos 2 caracteres.")
        return normalized


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    category: TaskCategory | None = None
    deadline: date | None = None
    assignee_id: int | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("O título deve ter pelo menos 2 caracteres.")
        return normalized


class TaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority: str
    category: str
    deadline: date | None
    project_id: int
    assignee_id: int | None
    assignee: UserPublic | None
    created_at: datetime


class ProjectTaskList(BaseModel):
    project_id: int
    tasks: list[TaskPublic]
