from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


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
    user_type: Mapped[str] = mapped_column(
        String(40), default="student", server_default=text("'student'")
    )
    course: Mapped[str | None] = mapped_column(String(160), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    owned_projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", foreign_keys="Project.owner_id"
    )
    led_projects: Mapped[list["Project"]] = relationship(
        back_populates="leader", foreign_keys="Project.leader_id"
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    projects = association_proxy(
        "project_memberships", "project",
        creator=lambda project: ProjectMember(project=project),
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="user", passive_deletes=True
    )
    uploaded_attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="uploaded_by"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
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
    status: Mapped[str] = mapped_column(
        String(30), default="active", server_default=text("'active'")
    )
    project_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    leader_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    owner: Mapped[User] = relationship(
        back_populates="owned_projects", foreign_keys=[owner_id]
    )
    leader: Mapped[User | None] = relationship(
        back_populates="led_projects", foreign_keys=[leader_id]
    )
    project_type: Mapped["ProjectType | None"] = relationship(back_populates="projects")
    team: Mapped["Team | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    members = association_proxy(
        "memberships", "user", creator=lambda user: ProjectMember(user=user)
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    stages: Mapped[list["Stage"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="Stage.order",
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        CheckConstraint(
            "role IN ('leader', 'member')", name="ck_project_members_role"
        ),
        Index("ix_project_members_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), default="member", server_default=text("'member'")
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="project_memberships")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 120", name="ck_teams_name_length"
        ),
        UniqueConstraint("project_id", name="uq_teams_project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    project: Mapped[Project] = relationship(back_populates="team")
    memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    members = association_proxy(
        "memberships", "user", creator=lambda user: TeamMember(user=user)
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        CheckConstraint(
            "role IN ('leader', 'member')", name="ck_team_members_role"
        ),
        Index("ix_team_members_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), default="member", server_default=text("'member'")
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    team: Mapped[Team] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="team_memberships")


class ProjectType(Base):
    __tablename__ = "project_types"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 80", name="ck_project_types_name_length"
        ),
        UniqueConstraint("name", name="uq_project_types_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    projects: Mapped[list[Project]] = relationship(back_populates="project_type")
    models: Mapped[list["ProjectModel"]] = relationship(
        back_populates="project_type", cascade="all, delete-orphan"
    )


class ProjectModel(Base):
    __tablename__ = "project_models"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 120", name="ck_project_models_name_length"
        ),
        Index("ix_project_models_project_type_id", "project_type_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    stage_structure: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, server_default=text("'[]'")
    )
    project_type_id: Mapped[int] = mapped_column(
        ForeignKey("project_types.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    project_type: Mapped[ProjectType] = relationship(back_populates="models")
    stages: Mapped[list["ModelStage"]] = relationship(
        back_populates="project_model",
        cascade="all, delete-orphan",
        order_by="ModelStage.order",
    )


class TaskStage(Base):
    __tablename__ = "task_stages"
    __table_args__ = (
        UniqueConstraint("task_id", "stage_id", name="uq_task_stages_task_stage"),
        Index("ix_task_stages_stage_id", "stage_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("model_stages.id", ondelete="CASCADE"), nullable=False
    )
    task: Mapped["Task"] = relationship(back_populates="stage_links")
    stage: Mapped["ModelStage"] = relationship(back_populates="task_links")


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
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("stages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    project: Mapped[Project] = relationship(back_populates="tasks")
    assignee: Mapped[User | None] = relationship()
    stage: Mapped["Stage | None"] = relationship(back_populates="tasks")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    stage_links: Mapped[list[TaskStage]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    stages = association_proxy(
        "stage_links", "stage", creator=lambda stage: TaskStage(stage=stage)
    )


class Stage(Base):
    __tablename__ = "stages"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 120", name="ck_stages_name_length"
        ),
        Index("ix_stages_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    project: Mapped[Project] = relationship(back_populates="stages")
    tasks: Mapped[list[Task]] = relationship(back_populates="stage")


class ModelStage(Base):
    __tablename__ = "model_stages"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 120", name="ck_model_stages_name_length"
        ),
        UniqueConstraint(
            "project_model_id", "order", name="uq_model_stages_model_order"
        ),
        Index("ix_model_stages_project_model_id", "project_model_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    project_model_id: Mapped[int] = mapped_column(
        ForeignKey("project_models.id", ondelete="CASCADE"), nullable=False
    )
    project_model: Mapped[ProjectModel] = relationship(back_populates="stages")
    task_links: Mapped[list[TaskStage]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )
    task_links: Mapped[list[TaskStage]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    task: Mapped[Task] = relationship(back_populates="comments")
    user: Mapped[User] = relationship(back_populates="comments")


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    file_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    task: Mapped[Task] = relationship(back_populates="attachments")
    uploaded_by: Mapped[User | None] = relationship(
        back_populates="uploaded_attachments"
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    notification_type: Mapped[str] = mapped_column(String(40))
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    user: Mapped[User] = relationship(back_populates="notifications")
