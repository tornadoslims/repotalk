"""Write .md mirror tree + graph artifacts (JSON, Mermaid)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from salt_doc_gen.config import Config
from salt_doc_gen.graph import KnowledgeGraph
from salt_doc_gen.models import (
    DirectorySummary,
    FileDocumentation,
    HashCache,
    ProjectSummary,
)

logger = logging.getLogger(__name__)

HASH_CACHE_FILE = ".salt-doc-gen-hashes.json"


def get_output_dir(root: Path, config: Config) -> Path:
    """Resolve the output directory."""
    output = Path(config.output.output_dir)
    if not output.is_absolute():
        output = root / output
    return output


def write_file_docs(
    docs: list[FileDocumentation],
    root: Path,
    config: Config,
) -> None:
    """Write per-file documentation as a mirror tree."""
    output_dir = get_output_dir(root, config)

    for doc in docs:
        # Mirror the source tree: foo/bar.py -> docs-mirror/foo/bar.py.md
        rel = Path(doc.relative_path)
        out_path = output_dir / f"{rel}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(doc.full_markdown)

    logger.info("Wrote %d file docs to %s", len(docs), output_dir)


def write_directory_summaries(
    summaries: list[DirectorySummary],
    root: Path,
    config: Config,
) -> None:
    """Write directory-level summaries."""
    output_dir = get_output_dir(root, config)

    for summary in summaries:
        out_path = output_dir / summary.relative_path / "_summary.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(summary.full_markdown)

    logger.info("Wrote %d directory summaries", len(summaries))


def write_project_summary(
    summary: ProjectSummary,
    root: Path,
    config: Config,
) -> None:
    """Write top-level project summary."""
    output_dir = get_output_dir(root, config)
    out_path = output_dir / "PROJECT_OVERVIEW.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(summary.full_markdown)
    logger.info("Wrote project summary to %s", out_path)


def write_graph(
    graph: KnowledgeGraph,
    root: Path,
    config: Config,
) -> None:
    """Write graph artifacts."""
    output_dir = get_output_dir(root, config)
    graph.save(output_dir)

    if config.output.generate_mermaid:
        mermaid = graph.to_mermaid()
        mermaid_path = output_dir / "knowledge_graph.mmd"
        mermaid_path.write_text(mermaid)


def write_analysis_cache(
    analyses: list,
    root: Path,
    config: Config,
) -> None:
    """Write analysis results as JSON cache."""
    output_dir = get_output_dir(root, config)
    output_dir.mkdir(parents=True, exist_ok=True)

    cache_path = output_dir / "analysis_cache.json"
    data = [a.model_dump() for a in analyses]
    cache_path.write_text(json.dumps(data, indent=2))
    logger.info("Analysis cache saved to %s", cache_path)


def load_analysis_cache(root: Path, config: Config) -> list | None:
    """Load cached analysis results."""
    output_dir = get_output_dir(root, config)
    cache_path = output_dir / "analysis_cache.json"

    if not cache_path.exists():
        return None

    try:
        from salt_doc_gen.models import FileAnalysis
        data = json.loads(cache_path.read_text())
        return [FileAnalysis(**item) for item in data]
    except Exception as e:
        logger.warning("Failed to load analysis cache: %s", e)
        return None


def load_hash_cache(root: Path, config: Config) -> HashCache:
    """Load or create hash cache for incremental updates."""
    output_dir = get_output_dir(root, config)
    cache_path = output_dir / HASH_CACHE_FILE

    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            return HashCache(**data)
        except Exception:
            pass

    return HashCache()


def save_hash_cache(cache: HashCache, root: Path, config: Config) -> None:
    """Save hash cache."""
    output_dir = get_output_dir(root, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / HASH_CACHE_FILE
    cache_path.write_text(json.dumps(cache.model_dump(), indent=2))


def load_file_docs(root: Path, config: Config) -> list[FileDocumentation]:
    """Load existing file documentation from the mirror tree."""
    output_dir = get_output_dir(root, config)
    docs = []

    if not output_dir.exists():
        return docs

    for md_file in output_dir.rglob("*.md"):
        rel = str(md_file.relative_to(output_dir))
        # Skip special files
        if rel.startswith("_") or rel == "PROJECT_OVERVIEW.md":
            continue
        if rel.endswith("_summary.md"):
            continue

        # Reconstruct relative source path (remove trailing .md)
        if rel.endswith(".py.md"):
            source_rel = rel[:-3]  # Remove .md
        else:
            continue

        content = md_file.read_text(errors="replace")
        docs.append(
            FileDocumentation(
                file_path=str(root / source_rel),
                relative_path=source_rel,
                full_markdown=content,
            )
        )

    return docs
