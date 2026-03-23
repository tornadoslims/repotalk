"""SQLAlchemy ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# --- Enums ---

class FileStatus(str, enum.Enum):
    pending = "pending"
    analyzed = "analyzed"
    documented = "documented"
    stale = "stale"


class NodeType(str, enum.Enum):
    file = "file"
    function = "function"
    class_ = "class"
    module = "module"
    directory = "directory"
    method = "method"
    variable = "variable"


class EdgeTypeEnum(str, enum.Enum):
    imports = "imports"
    calls = "calls"
    inherits = "inherits"
    composes = "composes"
    decorates = "decorates"
    defines = "defines"
    contains = "contains"


class SummaryStatus(str, enum.Enum):
    pending = "pending"
    generated = "generated"
    stale = "stale"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class UserRole(str, enum.Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class AnnotationTargetType(str, enum.Enum):
    file = "file"
    function = "function"
    class_ = "class"
    directory = "directory"
    edge = "edge"
    node = "node"


class AgentStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    completed = "completed"
    failed = "failed"
    killed = "killed"


# --- Models ---

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    graph_node_count: Mapped[int] = mapped_column(Integer, default=0)
    graph_edge_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    source_files: Mapped[list[SourceFile]] = relationship(back_populates="project", cascade="all, delete-orphan")
    graph_nodes: Mapped[list[GraphNodeRow]] = relationship(back_populates="project", cascade="all, delete-orphan")
    graph_edges: Mapped[list[GraphEdgeRow]] = relationship(back_populates="project", cascade="all, delete-orphan")
    directory_summaries: Mapped[list[DirectorySummaryRow]] = relationship(back_populates="project", cascade="all, delete-orphan")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="project", cascade="all, delete-orphan")
    annotations: Mapped[list[Annotation]] = relationship(back_populates="project", cascade="all, delete-orphan")
    agent_sessions: Mapped[list[AgentSession]] = relationship(back_populates="project", cascade="all, delete-orphan")


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_documented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    documentation_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FileStatus] = mapped_column(Enum(FileStatus), default=FileStatus.pending)

    project: Mapped[Project] = relationship(back_populates="source_files")
    graph_nodes: Mapped[list[GraphNodeRow]] = relationship(back_populates="source_file", cascade="all, delete-orphan")


class GraphNodeRow(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("source_files.id", ondelete="SET NULL"), nullable=True)
    node_type: Mapped[NodeType] = mapped_column(Enum(NodeType), nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)
    complexity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    project: Mapped[Project] = relationship(back_populates="graph_nodes")
    source_file: Mapped[SourceFile | None] = relationship(back_populates="graph_nodes")


class GraphEdgeRow(Base):
    __tablename__ = "graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_node_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    edge_type: Mapped[EdgeTypeEnum] = mapped_column(Enum(EdgeTypeEnum), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    llm_annotation: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(back_populates="graph_edges")
    source_node: Mapped[GraphNodeRow] = relationship(foreign_keys=[source_node_id])
    target_node: Mapped[GraphNodeRow] = relationship(foreign_keys=[target_node_id])


class DirectorySummaryRow(Base):
    __tablename__ = "directory_summaries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0)
    summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    child_count: Mapped[int] = mapped_column(Integer, default=0)
    total_file_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SummaryStatus] = mapped_column(Enum(SummaryStatus), default=SummaryStatus.pending)

    project: Mapped[Project] = relationship(back_populates="directory_summaries")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pinned_files: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project: Mapped[Project] = relationship(back_populates="conversations")
    user: Mapped[User | None] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    agent_sessions: Mapped[list[AgentSession]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    references: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    context_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_count_in: Mapped[int] = mapped_column(Integer, default=0)
    token_count_out: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    parent_message: Mapped[Message | None] = relationship(remote_side=[id])


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.member)
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="user")
    annotations: Mapped[list[Annotation]] = relationship(back_populates="user")
    agent_sessions: Mapped[list[AgentSession]] = relationship(back_populates="user")


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_type: Mapped[AnnotationTargetType] = mapped_column(Enum(AnnotationTargetType), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="annotations")
    user: Mapped[User | None] = relationship(back_populates="annotations")


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    agent_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    task_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_provided: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.pending)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="agent_sessions")
    user: Mapped[User | None] = relationship(back_populates="agent_sessions")
    conversation: Mapped[Conversation | None] = relationship(back_populates="agent_sessions")
