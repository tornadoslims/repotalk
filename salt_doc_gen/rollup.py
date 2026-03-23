"""Hierarchical summary generation (directory -> module -> top-level)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from salt_doc_gen.config import Config
from salt_doc_gen.graph import KnowledgeGraph
from salt_doc_gen.llm_client import LLMClient
from salt_doc_gen.models import DirectorySummary, FileDocumentation, ProjectSummary

logger = logging.getLogger(__name__)

PHASE = "rollup"


def _load_rollup_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "rollup.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return _DEFAULT_ROLLUP_PROMPT


_DEFAULT_ROLLUP_PROMPT = """\
You are a technical documentation writer. Given documentation for files in a directory, \
write a concise summary of what this directory/module does as a whole.

Focus on:
- The overall purpose and responsibility of this module/directory
- Key components and how they relate
- Public API surface (what do consumers of this module use?)
- Important patterns or conventions

Output markdown. Keep it concise (200-400 words).
"""


def _get_directory_tree(root: Path, output_dir: Path) -> dict[str, list[str]]:
    """Build a mapping of directory -> child directories (bottom-up order)."""
    dirs: dict[str, list[str]] = {}
    for md_file in sorted(output_dir.rglob("*.md")):
        rel = md_file.relative_to(output_dir)
        parent = str(rel.parent)
        if parent == ".":
            continue
        # Walk up parent chain
        parts = Path(parent).parts
        for i in range(len(parts)):
            d = str(Path(*parts[: i + 1]))
            if d not in dirs:
                dirs[d] = []
            if i + 1 < len(parts):
                child = str(Path(*parts[: i + 2]))
                if child not in dirs.get(d, []):
                    dirs[d].append(child)
    return dirs


async def rollup_directory(
    dir_path: str,
    file_docs: list[FileDocumentation],
    child_summaries: list[DirectorySummary],
    client: LLMClient,
    config: Config,
) -> DirectorySummary:
    """Generate a summary for a single directory from its file docs and child summaries."""
    system_prompt = _load_rollup_prompt()

    parts = [f"# Directory: {dir_path}\n"]

    # Include child directory summaries
    for child in child_summaries:
        parts.append(f"## Subdirectory: {child.relative_path}\n{child.summary}\n")

    # Include file docs (truncated)
    for doc in file_docs:
        # Use first 500 chars of each file doc
        truncated = doc.full_markdown[:500]
        parts.append(f"## File: {doc.relative_path}\n{truncated}\n")

    context = "\n".join(parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    model = config.models.rollup_summaries
    summary_text = await client.complete(
        messages=messages,
        model=model,
        phase=PHASE,
        file_path=dir_path,
        max_tokens=2048,
    )

    full_md = f"# {dir_path}/\n\n{summary_text}"

    return DirectorySummary(
        dir_path=dir_path,
        relative_path=dir_path,
        summary=summary_text,
        file_count=len(file_docs),
        child_summaries=[c.relative_path for c in child_summaries],
        full_markdown=full_md,
    )


async def rollup_all(
    file_docs: list[FileDocumentation],
    root: Path,
    client: LLMClient,
    config: Config,
    graph: KnowledgeGraph | None = None,
) -> tuple[list[DirectorySummary], ProjectSummary | None]:
    """Generate hierarchical summaries bottom-up.

    Returns (directory_summaries, project_summary).
    """
    # Group file docs by directory
    dir_files: dict[str, list[FileDocumentation]] = {}
    for doc in file_docs:
        parent = str(Path(doc.relative_path).parent)
        if parent == ".":
            parent = ""
        dir_files.setdefault(parent, []).append(doc)

    # Determine directory hierarchy and processing order (leaves first)
    all_dirs = set(dir_files.keys())
    # Add parent directories
    for d in list(all_dirs):
        parts = Path(d).parts if d else ()
        for i in range(len(parts)):
            all_dirs.add(str(Path(*parts[: i + 1])))
    all_dirs.discard("")

    # Sort by depth (deepest first) for bottom-up processing
    sorted_dirs = sorted(all_dirs, key=lambda d: d.count("/"), reverse=True)

    dir_summaries: dict[str, DirectorySummary] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("Rolling up summaries...", total=len(sorted_dirs))

        for dir_path in sorted_dirs:
            # Get file docs for this directory
            docs = dir_files.get(dir_path, [])

            # Get child summaries
            children = []
            for other_dir, summary in dir_summaries.items():
                if other_dir != dir_path and str(Path(other_dir).parent) == dir_path:
                    children.append(summary)

            if not docs and not children:
                progress.advance(task)
                continue

            try:
                summary = await rollup_directory(
                    dir_path, docs, children, client, config
                )
                dir_summaries[dir_path] = summary
            except Exception as e:
                logger.error("Error rolling up %s: %s", dir_path, e)

            progress.advance(task)

    # Generate top-level project summary
    project_summary = None
    top_level_summaries = [
        s for d, s in dir_summaries.items() if "/" not in d
    ]
    root_docs = dir_files.get("", [])

    if top_level_summaries or root_docs:
        try:
            project_summary = await _generate_project_summary(
                root, top_level_summaries, root_docs, client, config
            )
        except Exception as e:
            logger.error("Error generating project summary: %s", e)

    return list(dir_summaries.values()), project_summary


async def _generate_project_summary(
    root: Path,
    dir_summaries: list[DirectorySummary],
    root_docs: list[FileDocumentation],
    client: LLMClient,
    config: Config,
) -> ProjectSummary:
    """Generate top-level project summary."""
    parts = [f"# Project: {root.name}\n"]

    for summary in dir_summaries:
        parts.append(f"## Module: {summary.relative_path}\n{summary.summary[:300]}\n")

    for doc in root_docs:
        parts.append(f"## Root file: {doc.relative_path}\n{doc.full_markdown[:300]}\n")

    context = "\n".join(parts)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a technical writer. Generate a top-level project overview. "
                "Include: project purpose, architecture overview, key modules, and how they connect. "
                "Output markdown. Be concise but comprehensive (300-600 words)."
            ),
        },
        {"role": "user", "content": context},
    ]

    model = config.models.rollup_summaries
    content = await client.complete(
        messages=messages,
        model=model,
        phase=PHASE,
        file_path="PROJECT",
        max_tokens=2048,
    )

    return ProjectSummary(
        root_path=str(root),
        summary=content,
        full_markdown=f"# {root.name} — Project Overview\n\n{content}",
    )
