"""YAML config loader with Pydantic validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

DEFAULT_CONFIG_NAMES = ["repotalk.yaml", "config.yaml"]


class ApiKeysConfig(BaseModel):
    openai: str = ""
    anthropic: str = ""
    google: str = ""

    @model_validator(mode="after")
    def set_env_vars(self) -> "ApiKeysConfig":
        """Push API keys into environment so litellm picks them up."""
        if self.openai:
            os.environ.setdefault("OPENAI_API_KEY", self.openai)
        if self.anthropic:
            os.environ.setdefault("ANTHROPIC_API_KEY", self.anthropic)
        if self.google:
            os.environ.setdefault("GEMINI_API_KEY", self.google)
        return self


class ModelsConfig(BaseModel):
    file_documentation: str = "gemini/gemini-2.5-flash"
    graph_enrichment: str = "gemini/gemini-2.5-flash"
    rollup_summaries: str = "gemini/gemini-2.5-pro"
    chat: str = "anthropic/claude-sonnet-4-20250514"
    embeddings: str = "openai/text-embedding-3-small"


class ProcessingConfig(BaseModel):
    concurrency: int = 10
    skip_tiny_files: bool = True
    tiny_file_threshold: int = 10
    file_extensions: list[str] = Field(default_factory=lambda: [".py"])
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "**/test_*",
            "**/.git/**",
            "**/migrations/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/.venv/**",
        ]
    )


class OutputConfig(BaseModel):
    output_dir: str = "./docs-mirror"
    graph_format: str = "json"
    generate_mermaid: bool = True
    include_source_links: bool = True


class ChatConfig(BaseModel):
    retrieval_method: str = "keyword"  # keyword or vector
    top_k: int = 10
    include_source: bool = True
    history_length: int = 10


class Config(BaseModel):
    api_keys: ApiKeysConfig = Field(default_factory=ApiKeysConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    chat: ChatConfig = Field(default_factory=ChatConfig)


def find_config(start_path: Path) -> Path | None:
    """Walk up from start_path looking for config file."""
    current = start_path.resolve()
    for directory in [current] + list(current.parents):
        for name in DEFAULT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate
    return None


def find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml walking up from this file."""
    current = Path(__file__).resolve().parent
    for directory in [current] + list(current.parents):
        if (directory / "pyproject.toml").exists():
            return directory
    return Path.cwd()


def load_config(config_path: Path | None = None, target_path: Path | None = None) -> Config:
    """Load and validate config from YAML file.

    Resolution order:
    1. Explicit config_path if given
    2. Walk up from target_path looking for repotalk.yaml
    3. Fall back to defaults
    """
    if config_path and config_path.exists():
        return _parse_config_file(config_path)

    if target_path:
        found = find_config(target_path)
        if found:
            return _parse_config_file(found)

    return Config()


def _parse_config_file(path: Path) -> Config:
    """Parse a YAML config file into a Config object."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    return Config(**raw)
