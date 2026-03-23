"""Pydantic request/response schemas for all API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Projects ---

class ProjectCreate(BaseModel):
    name: str
    source_path: str
    config: dict[str, Any] | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None

class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    source_path: str
    output_path: str | None = None
    config: dict[str, Any] | None = None
    last_indexed_at: datetime | None = None
    file_count: int = 0
    graph_node_count: int = 0
    graph_edge_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ProjectStats(ProjectOut):
    conversation_count: int = 0
    annotation_count: int = 0

class IndexStatus(BaseModel):
    project_id: uuid.UUID
    status: str  # started, running, completed, failed
    task_id: str | None = None
    message: str = ""


# --- Source Files ---

class SourceFileOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    relative_path: str
    content_hash: str | None = None
    line_count: int = 0
    token_estimate: int = 0
    language: str | None = None
    last_analyzed_at: datetime | None = None
    last_documented_at: datetime | None = None
    status: str
    documentation_md: str | None = None

    model_config = {"from_attributes": True}

class SourceFileDetail(SourceFileOut):
    analysis_data: dict[str, Any] | None = None


# --- Graph ---

class GraphNodeOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_file_id: uuid.UUID | None = None
    node_type: str
    qualified_name: str
    display_name: str
    line_start: int | None = None
    line_end: int | None = None
    signature: str | None = None
    docstring: str | None = None
    complexity: int | None = None
    metadata: dict[str, Any] | None = Field(None, alias="extra_metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}

class GraphEdgeOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    weight: float = 1.0
    metadata: dict[str, Any] | None = Field(None, alias="extra_metadata")
    llm_annotation: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}

class GraphOut(BaseModel):
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    stats: dict[str, int] = Field(default_factory=dict)

class SubgraphRequest(BaseModel):
    node: str
    depth: int = 2

class NodeDetail(GraphNodeOut):
    incoming_edges: list[GraphEdgeOut] = Field(default_factory=list)
    outgoing_edges: list[GraphEdgeOut] = Field(default_factory=list)

class TraceResult(BaseModel):
    root_node_id: uuid.UUID
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    depth: int

class ImpactResult(BaseModel):
    target_node_id: uuid.UUID
    affected_nodes: list[GraphNodeOut]
    affected_edges: list[GraphEdgeOut]
    depth: int

class SimilarNode(BaseModel):
    node: GraphNodeOut
    similarity_score: float

class MermaidOut(BaseModel):
    diagram: str
    node_count: int


# --- Documentation ---

class DocTreeNode(BaseModel):
    path: str
    name: str
    type: str  # file, directory
    children: list[DocTreeNode] = Field(default_factory=list)
    has_doc: bool = False

class DocOut(BaseModel):
    path: str
    content: str
    doc_type: str = "file"

class DocSearchResult(BaseModel):
    path: str
    snippet: str
    relevance: float = 0.0
    doc_type: str = "file"


# --- Chat ---

class ConversationCreate(BaseModel):
    title: str | None = None
    scope: str | None = None
    pinned_files: list[str] | None = None

class ConversationOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None = None
    title: str | None = None
    scope: str | None = None
    pinned_files: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class MessageCreate(BaseModel):
    content: str
    pinned_files: list[str] | None = None

class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    references: dict[str, Any] | None = None
    context_used: dict[str, Any] | None = None
    model_used: str | None = None
    token_count_in: int = 0
    token_count_out: int = 0
    cost: float = 0.0
    parent_message_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

class BranchRequest(BaseModel):
    content: str


# --- Context Export ---

class ContextExportRequest(BaseModel):
    query: str
    depth: int = 2
    max_tokens: int = 8000

class ContextExportResponse(BaseModel):
    docs: list[dict[str, Any]]
    graph: dict[str, Any] | None = None
    source_snippets: list[dict[str, str]] = Field(default_factory=list)
    total_tokens: int = 0


# --- Annotations ---

class AnnotationCreate(BaseModel):
    target_type: str
    target_id: str
    content: str

class AnnotationOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None = None
    target_type: str
    target_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Agents ---

class AgentRunRequest(BaseModel):
    agent_type: str = "coding"
    task_description: str
    context: dict[str, Any] | None = None
    conversation_id: uuid.UUID | None = None

class AgentSessionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    agent_type: str | None = None
    task_description: str | None = None
    status: str
    branch_name: str | None = None
    result_summary: str | None = None
    pr_url: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Webhooks ---

class WebhookPayload(BaseModel):
    """Generic webhook payload - specific fields vary by provider."""
    model_config = {"extra": "allow"}

class WatcherStatus(BaseModel):
    project_id: uuid.UUID
    active: bool
    watched_path: str | None = None
    last_event_at: datetime | None = None
    events_since_start: int = 0

class WatcherConfig(BaseModel):
    active: bool | None = None
    debounce_seconds: float | None = None

class UpdateLogEntry(BaseModel):
    timestamp: datetime
    event_type: str
    path: str | None = None
    details: str = ""


# --- Settings ---

class SettingsOut(BaseModel):
    models: dict[str, str] = Field(default_factory=dict)
    processing: dict[str, Any] = Field(default_factory=dict)
    chat: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)

class SettingsUpdate(BaseModel):
    models: dict[str, str] | None = None
    processing: dict[str, Any] | None = None
    chat: dict[str, Any] | None = None
    output: dict[str, Any] | None = None

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int = 0
    supports_streaming: bool = True

class UsageStats(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    by_phase: dict[str, Any] = Field(default_factory=dict)
    by_model: dict[str, Any] = Field(default_factory=dict)


# --- Users ---

class UserCreate(BaseModel):
    username: str
    email: str | None = None
    role: str = "member"

class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
    preferences: dict[str, Any] | None = None

class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    role: str
    preferences: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Health ---

class HealthOut(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    database: str = "connected"
