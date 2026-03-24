"""Per-file LLM documentation with structured output."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from typing import Any, Callable

from repotalk.config import Config
from repotalk.graph import KnowledgeGraph
from repotalk.llm_client import LLMClient
from repotalk.models import FileAnalysis, FileDocumentation, HashCache

logger = logging.getLogger(__name__)

PHASE = "file_documentation"


def _load_prompt_template() -> str:
    """Load the file documentation prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "file_doc.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return _DEFAULT_PROMPT


_DEFAULT_PROMPT = """\
You are a technical documentation writer. Generate comprehensive documentation for the given Python source file.

Structure your output as markdown with these exact sections:

## Purpose
A 2-3 sentence summary of what this file/module does and why it exists.

## Dependencies
List key imports and what they're used for. Distinguish internal vs external dependencies.

## Classes
For each class: purpose, key methods, inheritance. Skip if no classes.

## Functions
For each function: purpose, parameters, return value, side effects. Skip if no functions.

## Data Flow
How data moves through this module — inputs, transformations, outputs.

## Side Effects
Any I/O, state mutations, environment changes, or external calls.
"""


def _build_file_context(
    analysis: FileAnalysis,
    source: str,
    graph: KnowledgeGraph | None = None,
) -> str:
    """Build the context string sent to the LLM for a single file."""
    parts = [
        f"# File: {analysis.relative_path}",
        f"Module: {analysis.module_name}",
        f"Lines: {analysis.line_count}",
    ]

    if analysis.module_docstring:
        parts.append(f"\nModule docstring: {analysis.module_docstring}")

    # Imports summary
    if analysis.imports:
        parts.append("\n## Imports")
        for imp in analysis.imports:
            tag = " (internal)" if imp.is_internal else ""
            names = ", ".join(imp.names) if imp.names else imp.module
            parts.append(f"- from {imp.module} import {names}{tag}")

    # Classes summary
    if analysis.classes:
        parts.append("\n## Classes")
        for cls in analysis.classes:
            bases = f"({', '.join(cls.bases)})" if cls.bases else ""
            parts.append(f"- {cls.name}{bases} [lines {cls.line_start}-{cls.line_end}]")
            if cls.docstring:
                parts.append(f"  Docstring: {cls.docstring[:200]}")
            for method in cls.methods:
                args = ", ".join(a.name for a in method.args)
                ret = f" -> {method.return_type}" if method.return_type else ""
                parts.append(f"  - {method.name}({args}){ret}")

    # Functions summary
    if analysis.functions:
        parts.append("\n## Functions")
        for func in analysis.functions:
            args = ", ".join(a.name for a in func.args)
            ret = f" -> {func.return_type}" if func.return_type else ""
            async_prefix = "async " if func.is_async else ""
            parts.append(f"- {async_prefix}{func.name}({args}){ret} [lines {func.line_start}-{func.line_end}]")
            if func.docstring:
                parts.append(f"  Docstring: {func.docstring[:200]}")
            if func.calls:
                parts.append(f"  Calls: {', '.join(func.calls[:10])}")

    # Variables
    if analysis.variables:
        parts.append("\n## Module Variables")
        for var in analysis.variables:
            ann = f": {var.annotation}" if var.annotation else ""
            parts.append(f"- {var.name}{ann}")

    # Graph context
    if graph:
        deps = graph.get_file_dependencies(analysis.relative_path)
        if deps:
            parts.append(f"\n## Dependencies (graph): {', '.join(deps)}")
        dependents = graph.get_file_dependents(analysis.relative_path)
        if dependents:
            parts.append(f"## Used by: {', '.join(dependents)}")

    # Source code
    parts.append(f"\n## Source Code\n```python\n{source}\n```")

    return "\n".join(parts)


async def document_file(
    analysis: FileAnalysis,
    root: Path,
    client: LLMClient,
    config: Config,
    graph: KnowledgeGraph | None = None,
) -> FileDocumentation:
    """Generate documentation for a single file."""
    file_path = Path(analysis.file_path)
    source = file_path.read_text(errors="replace")

    system_prompt = _load_prompt_template()
    context = _build_file_context(analysis, source, graph)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    model = config.models.file_documentation
    content = await client.complete(
        messages=messages,
        model=model,
        phase=PHASE,
        file_path=analysis.relative_path,
        max_tokens=4096,
    )

    # Build the full markdown
    header = f"# {analysis.relative_path}\n\n"
    if config.output.include_source_links:
        header += f"> Source: `{analysis.relative_path}`\n\n"

    full_md = header + content

    return FileDocumentation(
        file_path=analysis.file_path,
        relative_path=analysis.relative_path,
        full_markdown=full_md,
        file_hash=analysis.file_hash,
    )


async def document_all(
    analyses: list[FileAnalysis],
    root: Path,
    client: LLMClient,
    config: Config,
    graph: KnowledgeGraph | None = None,
    hash_cache: HashCache | None = None,
    on_progress: "Callable[[int, int, str], Any] | None" = None,
) -> list[FileDocumentation]:
    """Generate documentation for all files, with incremental support.
    
    Args:
        on_progress: Optional async/sync callback(completed, total, file_path)
                     called after each file is documented.
    """
    to_process = []
    skipped = 0

    for analysis in analyses:
        if hash_cache and not hash_cache.is_changed(analysis.relative_path, analysis.file_hash):
            skipped += 1
            continue
        to_process.append(analysis)

    if skipped:
        logger.info("Skipping %d unchanged files", skipped)

    if not to_process:
        logger.info("No files to document")
        return []

    docs: list[FileDocumentation] = []
    errors = 0
    completed = 0
    use_rich = on_progress is None  # Only show Rich bar in CLI mode

    progress_ctx = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) if use_rich else None

    async def _process(analysis: FileAnalysis) -> FileDocumentation | None:
        nonlocal errors, completed
        try:
            doc = await document_file(analysis, root, client, config, graph)
            if hash_cache:
                hash_cache.update(analysis.relative_path, analysis.file_hash)
            return doc
        except Exception as e:
            errors += 1
            logger.error("Error documenting %s: %s", analysis.relative_path, e)
            return None
        finally:
            completed += 1
            if progress_ctx and task_id is not None:
                progress_ctx.advance(task_id)
            if on_progress:
                try:
                    result = on_progress(completed, len(to_process), analysis.relative_path)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass

    task_id = None
    if progress_ctx:
        progress_ctx.start()
        task_id = progress_ctx.add_task("Documenting files...", total=len(to_process))

    try:
        tasks = [_process(a) for a in to_process]
        results = await asyncio.gather(*tasks)
        docs = [d for d in results if d is not None]
    finally:
        if progress_ctx:
            progress_ctx.stop()

    logger.info("Documented %d files (%d errors)", len(docs), errors)
    return docs
