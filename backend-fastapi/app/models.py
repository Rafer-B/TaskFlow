from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base

project_members = Table(
    "project_members",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)
Index("ix_project_members_user_id", project_members.c.user_id)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 2 AND 120",
            name="ck_users_name_length",
        ),
        CheckConstraint(
            "email = lower(trim(email)) AND length(email) > 0",
            name="ck_users_email_normalized",
        ),
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    owned_projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    projects: Mapped[list["Project"]] = relationship(
        secondary=project_members, back_populates="members"
    )


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 2 AND 160",
            name="ck_projects_name_length",
        ),
        CheckConstraint(
            "category IN ('Investigação', 'Desenvolvimento', 'Seminário', "
            "'Estudo de caso', 'Outro')",
            name="ck_projects_category",
        ),
        CheckConstraint(
            "length(color) = 7 AND substr(color, 1, 1) = '#'",
            name="ck_projects_color",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(
        Text, default="", server_default=text("''")
    )
    category: Mapped[str] = mapped_column(
        String(40), default="Desenvolvimento", server_default=text("'Desenvolvimento'")
    )
    color: Mapped[str] = mapped_column(
        String(20), default="#6c63ff", server_default=text("'#6c63ff'")
    )
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    owner: Mapped[User] = relationship(back_populates="owned_projects")
    members: Mapped[list[User]] = relationship(
        secondary=project_members, back_populates="projects"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) BETWEEN 2 AND 200",
            name="ck_tasks_title_length",
        ),
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'done', 'blocked')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_tasks_priority",
        ),
        CheckConstraint(
            "category IN ('Planeamento', 'Pesquisa', 'Conceção', "
            "'Execução', 'Validação', 'Documentação')",
            name="ck_tasks_category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(
        Text, default="", server_default=text("''")
    )
    status: Mapped[str] = mapped_column(
        String(20), default="todo", server_default=text("'todo'"), index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="medium", server_default=text("'medium'"), index=True
    )
    category: Mapped[str] = mapped_column(
        String(40), default="Execução", server_default=text("'Execução'")
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    project: Mapped[Project] = relationship(back_populates="tasks")
    assignee: Mapped[User | None] = relationship()
