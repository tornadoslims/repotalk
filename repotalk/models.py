"""Pydantic data models for all entities in repotalk."""

from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# --- AST Analysis Models ---


class ImportInfo(BaseModel):
    """A single import statement."""

    module: str
    names: list[str] = Field(default_factory=list)
    alias: str | None = None
    is_relative: bool = False
    is_internal: bool = False
    line: int = 0


class ArgumentInfo(BaseModel):
    """A function argument."""

    name: str
    annotation: str | None = None
    default: str | None = None


class FunctionInfo(BaseModel):
    """A function or method definition."""

    name: str
    qualified_name: str = ""
    args: list[ArgumentInfo] = Field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = Field(default_factory=list)
    docstring: str | None = None
    is_method: bool = False
    is_async: bool = False
    line_start: int = 0
    line_end: int = 0
    calls: list[str] = Field(default_factory=list)
    complexity: int = 1


class ClassInfo(BaseModel):
    """A class definition."""

    name: str
    qualified_name: str = ""
    bases: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    docstring: str | None = None
    methods: list[FunctionInfo] = Field(default_factory=list)
    class_variables: list[str] = Field(default_factory=list)
    line_start: int = 0
    line_end: int = 0


class VariableInfo(BaseModel):
    """A module-level variable."""

    name: str
    annotation: str | None = None
    value_repr: str | None = None
    line: int = 0


class FileAnalysis(BaseModel):
    """Complete AST analysis of a single file."""

    file_path: str
    relative_path: str = ""
    module_name: str = ""
    file_hash: str = ""
    line_count: int = 0
    imports: list[ImportInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)
    variables: list[VariableInfo] = Field(default_factory=list)
    module_docstring: str | None = None
    all_exports: list[str] | None = None
    errors: list[str] = Field(default_factory=list)

    def compute_hash(self) -> str:
        content = Path(self.file_path).read_bytes()
        return hashlib.sha256(content).hexdigest()


# --- Knowledge Graph Models ---


class EdgeType(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    COMPOSES = "composes"
    DECORATES = "decorates"
    DEFINES = "defines"
    CONTAINS = "contains"


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: str
    type: str  # file, function, class, module, directory
    name: str
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""

    source: str
    target: str
    edge_type: EdgeType
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Documentation Models ---


class FileDocumentation(BaseModel):
    """Generated documentation for a single file."""

    file_path: str
    relative_path: str = ""
    purpose: str = ""
    dependencies: str = ""
    classes_section: str = ""
    functions_section: str = ""
    data_flow: str = ""
    side_effects: str = ""
    full_markdown: str = ""
    file_hash: str = ""
    tokens_used: int = 0
    cost: float = 0.0


class DirectorySummary(BaseModel):
    """Rolled-up summary for a directory."""

    dir_path: str
    relative_path: str = ""
    summary: str = ""
    file_count: int = 0
    child_summaries: list[str] = Field(default_factory=list)
    full_markdown: str = ""
    tokens_used: int = 0
    cost: float = 0.0


class ProjectSummary(BaseModel):
    """Top-level project summary."""

    root_path: str
    summary: str = ""
    architecture: str = ""
    key_modules: list[str] = Field(default_factory=list)
    full_markdown: str = ""
    tokens_used: int = 0
    cost: float = 0.0


# --- Cost Tracking ---


class CostRecord(BaseModel):
    """Track LLM usage and costs for a single call."""

    phase: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    file_path: str | None = None


class PhaseStats(BaseModel):
    """Aggregate stats for a processing phase."""

    phase: str
    files_processed: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    errors: int = 0
    records: list[CostRecord] = Field(default_factory=list)

    def add_record(self, record: CostRecord) -> None:
        self.records.append(record)
        self.files_processed += 1
        self.total_input_tokens += record.input_tokens
        self.total_output_tokens += record.output_tokens
        self.total_cost += record.cost


# --- Chat Models ---


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # user, assistant, system
    content: str


class RetrievedContext(BaseModel):
    """A piece of context retrieved for RAG."""

    source: str
    content: str
    relevance_score: float = 0.0
    doc_type: str = "file"  # file, directory, project


# --- Hash Cache ---


class HashCache(BaseModel):
    """Cache of file hashes for incremental updates."""

    hashes: dict[str, str] = Field(default_factory=dict)

    def is_changed(self, file_path: str, current_hash: str) -> bool:
        return self.hashes.get(file_path) != current_hash

    def update(self, file_path: str, file_hash: str) -> None:
        self.hashes[file_path] = file_hash
