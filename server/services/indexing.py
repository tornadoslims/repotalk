"""Indexing service — full and incremental indexing using the core engine."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.database import async_session
from server.models_db import (
    DirectorySummaryRow,
    FileStatus,
    GraphEdgeRow,
    GraphNodeRow,
    NodeType,
    EdgeTypeEnum,
    Project,
    SourceFile,
    SummaryStatus,
)

logger = logging.getLogger("repotalk.indexing")

# Track running tasks and their progress
_running_tasks: dict[uuid.UUID, asyncio.Task] = {}
_progress: dict[uuid.UUID, dict] = {}


def get_task(project_id: uuid.UUID) -> asyncio.Task | None:
    return _running_tasks.get(project_id)


def get_progress(project_id: uuid.UUID) -> dict | None:
    return _progress.get(project_id)


async def _broadcast_progress(project_id: uuid.UUID, phase: str, message: str, progress: float = 0.0, **extra):
    """Broadcast indexing progress via WebSocket and store in memory for polling."""
    info = {
        "phase": phase,
        "message": message,
        "progress": round(progress, 3),
        **extra,
    }
    _progress[project_id] = info
    try:
        from server.main import ws_manager
        await ws_manager.send_to_project(project_id, "index_progress", info)
    except Exception:
        pass  # WebSocket not available


async def run_full_index(project_id: uuid.UUID, config: Any, llm_client: Any) -> None:
    """Full re-index: crawl, analyze, build graph, document, rollup."""
    task = asyncio.current_task()
    if task:
        _running_tasks[project_id] = task

    try:
        async with async_session() as db:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                logger.error("Project %s not found", project_id)
                return

            root = Path(project.source_path)
            if not root.is_dir():
                logger.error("Source path %s is not a directory", root)
                await _broadcast_progress(project_id, "error", f"Source path not found: {root}")
                return

            logger.info("Starting full index for project %s at %s", project.name, root)
            await _broadcast_progress(project_id, "crawl", "Crawling files...", 0.0)

            # Phase 1: Crawl
            from repotalk.crawler import crawl
            files = crawl(root, config)
            logger.info("Crawled %d files", len(files))
            await _broadcast_progress(project_id, "analyze", f"Analyzing {len(files)} files...", 0.1)

            # Phase 2: Analyze
            from repotalk.analyzer import analyze_file
            analyses = []
            for i, fp in enumerate(files):
                try:
                    analysis = analyze_file(fp, root)
                    analyses.append(analysis)
                except Exception as exc:
                    logger.warning("Failed to analyze %s: %s", fp, exc)
                if (i + 1) % 10 == 0:
                    await _broadcast_progress(
                        project_id, "analyze",
                        f"Analyzed {i + 1}/{len(files)} files...",
                        0.1 + 0.2 * (i + 1) / len(files)
                    )

            await _broadcast_progress(project_id, "graph", "Building knowledge graph...", 0.3)

            # Phase 3: Build knowledge graph
            from repotalk.graph import KnowledgeGraph
            graph = KnowledgeGraph()
            graph.build_from_analyses(analyses)
            graph_stats = graph.stats()

            # Phase 4: Document files (async) with per-file progress
            # Uses hash cache: unchanged files are skipped, docs written to disk immediately
            from repotalk.documenter import document_all
            from repotalk.output import get_output_dir as _get_output_dir, load_hash_cache, save_hash_cache
            hash_cache = load_hash_cache(root, config)
            pre_output_dir = _get_output_dir(root, config)

            # Count how many files actually need documenting (for accurate progress)
            need_doc = sum(1 for a in analyses if hash_cache.is_changed(a.relative_path, a.file_hash))
            already_done = len(analyses) - need_doc
            await _broadcast_progress(project_id, "document",
                                     f"Documenting {need_doc} files ({already_done} cached)...", 0.35,
                                     files_total=need_doc, files_done=0)

            async def _doc_progress(done: int, total: int, file_path: str):
                await _broadcast_progress(
                    project_id, "document",
                    f"Documenting files ({done}/{total})... {file_path}",
                    0.35 + 0.35 * (done / max(total, 1)),
                    files_total=total, files_done=done, current_file=file_path,
                )

            file_docs = await document_all(analyses, root, llm_client, config, graph, hash_cache,
                                           on_progress=_doc_progress)
            save_hash_cache(hash_cache, root, config)

            # Also load docs from disk for files that were cached (already documented in prior runs)
            # This ensures the full set is available for rollup and DB persist
            from repotalk.models import FileDocumentation
            doc_paths_on_disk = {str(p.relative_to(pre_output_dir)): p
                                 for p in pre_output_dir.rglob("*.py.md")}
            file_doc_set = {d.relative_path for d in file_docs}
            for analysis in analyses:
                if analysis.relative_path not in file_doc_set:
                    md_key = f"{analysis.relative_path}.md"
                    disk_path = doc_paths_on_disk.get(md_key)
                    if disk_path and disk_path.exists():
                        content = disk_path.read_text(errors="replace")
                        file_docs.append(FileDocumentation(
                            file_path=analysis.file_path,
                            relative_path=analysis.relative_path,
                            full_markdown=content,
                            file_hash=analysis.file_hash,
                        ))
            logger.info("Total file docs: %d (%d new, %d from cache)",
                        len(file_docs), need_doc - (len(analyses) - len(file_docs)), already_done)

            await _broadcast_progress(project_id, "rollup", "Generating summaries...", 0.7)

            # Phase 5: Rollup summaries
            from repotalk.rollup import rollup_all
            dir_summaries, project_summary = await rollup_all(file_docs, root, llm_client, config, graph)

            await _broadcast_progress(project_id, "output", "Writing outputs...", 0.85)

            # Phase 6: Write outputs
            from repotalk.output import (
                get_output_dir,
                write_analysis_cache,
                write_directory_summaries,
                write_file_docs,
                write_graph,
                write_project_summary,
            )
            write_file_docs(file_docs, root, config)
            write_directory_summaries(dir_summaries, root, config)
            if project_summary:
                write_project_summary(project_summary, root, config)
            write_graph(graph, root, config)
            write_analysis_cache(analyses, root, config)

            output_dir = get_output_dir(root, config)

            # Phase 6.5: Build vector index for RAG chat
            await _broadcast_progress(project_id, "embedding", "Building vector search index...", 0.87)
            try:
                from repotalk.retriever import VectorRetriever
                vector_retriever = VectorRetriever(config, output_dir)
                await vector_retriever._ensure_collection()
                logger.info("Vector index built for %s", project.name)
            except Exception as exc:
                logger.warning("Vector indexing failed (chat will use keyword search): %s", exc)

            await _broadcast_progress(project_id, "persist", "Saving to database...", 0.9)

            # Phase 7: Persist to database
            now = datetime.now(timezone.utc)

            # Clear old data
            await db.execute(delete(SourceFile).where(SourceFile.project_id == project_id))
            await db.execute(delete(GraphNodeRow).where(GraphNodeRow.project_id == project_id))
            await db.execute(delete(GraphEdgeRow).where(GraphEdgeRow.project_id == project_id))
            await db.execute(delete(DirectorySummaryRow).where(DirectorySummaryRow.project_id == project_id))

            # Insert source files
            file_doc_map = {d.relative_path: d for d in file_docs}
            source_file_map: dict[str, SourceFile] = {}

            for analysis in analyses:
                doc = file_doc_map.get(analysis.relative_path)
                sf = SourceFile(
                    project_id=project_id,
                    relative_path=analysis.relative_path,
                    content_hash=analysis.file_hash,
                    line_count=analysis.line_count,
                    token_estimate=analysis.line_count * 4,  # rough estimate
                    language=_detect_language(analysis.relative_path),
                    last_analyzed_at=now,
                    last_documented_at=now if doc else None,
                    analysis_data=analysis.model_dump(),
                    documentation_md=doc.full_markdown if doc else None,
                    status=FileStatus.documented if doc else FileStatus.analyzed,
                )
                db.add(sf)
                source_file_map[analysis.relative_path] = sf

            await db.flush()

            # Insert graph nodes
            graph_json = graph.to_json()
            node_id_map: dict[str, uuid.UUID] = {}

            for gn in graph_json.get("nodes", []):
                node_type_str = gn.get("type", "file")
                try:
                    nt = NodeType(node_type_str)
                except ValueError:
                    nt = NodeType.file

                file_path = gn.get("file_path")
                sf_obj = source_file_map.get(file_path) if file_path else None
                meta = gn.get("metadata", {})

                row = GraphNodeRow(
                    project_id=project_id,
                    source_file_id=sf_obj.id if sf_obj else None,
                    node_type=nt,
                    qualified_name=gn["id"],
                    display_name=gn.get("name", gn["id"]),
                    line_start=meta.get("line_start"),
                    line_end=meta.get("line_end"),
                    signature=meta.get("signature"),
                    docstring=meta.get("docstring"),
                    complexity=meta.get("complexity"),
                    extra_metadata=meta,
                )
                db.add(row)
                await db.flush()
                node_id_map[gn["id"]] = row.id

            # Insert graph edges
            for ge in graph_json.get("edges", []):
                src_uuid = node_id_map.get(ge["source"])
                tgt_uuid = node_id_map.get(ge["target"])
                if not src_uuid or not tgt_uuid:
                    continue
                try:
                    et = EdgeTypeEnum(ge["edge_type"])
                except ValueError:
                    continue

                row = GraphEdgeRow(
                    project_id=project_id,
                    source_node_id=src_uuid,
                    target_node_id=tgt_uuid,
                    edge_type=et,
                    weight=ge.get("weight", 1.0),
                    extra_metadata=ge.get("metadata"),
                )
                db.add(row)

            # Insert directory summaries
            for ds in dir_summaries:
                row = DirectorySummaryRow(
                    project_id=project_id,
                    relative_path=ds.relative_path or ds.dir_path,
                    level=ds.relative_path.count("/") if ds.relative_path else 0,
                    summary_md=ds.full_markdown,
                    child_count=len(ds.child_summaries),
                    total_file_count=ds.file_count,
                    generated_at=now,
                    status=SummaryStatus.generated,
                )
                db.add(row)

            # Update project stats
            project.last_indexed_at = now
            project.file_count = len(analyses)
            project.graph_node_count = len(graph_json.get("nodes", []))
            project.graph_edge_count = len(graph_json.get("edges", []))
            project.output_path = str(output_dir)

            await db.commit()
            logger.info("Full index complete for %s: %d files, %d nodes, %d edges",
                        project.name, len(analyses), project.graph_node_count, project.graph_edge_count)

            await _broadcast_progress(project_id, "complete", "Indexing complete!", 1.0)

    except Exception:
        logger.exception("Full index failed for project %s", project_id)
        await _broadcast_progress(project_id, "error", "Indexing failed - check server logs")
    finally:
        _running_tasks.pop(project_id, None)


async def run_incremental_index(project_id: uuid.UUID, config: Any, llm_client: Any) -> None:
    """Incremental index: only re-process changed files."""
    task = asyncio.current_task()
    if task:
        _running_tasks[project_id] = task

    try:
        async with async_session() as db:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                return

            root = Path(project.source_path)
            if not root.is_dir():
                return

            from repotalk.crawler import crawl
            from repotalk.analyzer import analyze_file
            from repotalk.output import load_hash_cache, save_hash_cache

            files = crawl(root, config)
            hash_cache = load_hash_cache(root, config)

            changed_files = []
            all_analyses = []
            for fp in files:
                try:
                    analysis = analyze_file(fp, root)
                    all_analyses.append(analysis)
                    current_hash = analysis.file_hash or analysis.compute_hash()
                    if hash_cache.is_changed(analysis.relative_path, current_hash):
                        changed_files.append(analysis)
                        hash_cache.update(analysis.relative_path, current_hash)
                except Exception as exc:
                    logger.warning("Failed to analyze %s: %s", fp, exc)

            if not changed_files:
                logger.info("No changed files for project %s", project.name)
                _running_tasks.pop(project_id, None)
                return

            logger.info("Incremental index: %d changed files out of %d", len(changed_files), len(files))

            # Rebuild graph with all analyses
            from repotalk.graph import KnowledgeGraph
            graph = KnowledgeGraph()
            graph.build_from_analyses(all_analyses)

            # Re-document only changed files
            from repotalk.documenter import document_all
            new_docs = await document_all(changed_files, root, llm_client, config, graph, hash_cache)
            save_hash_cache(hash_cache, root, config)

            # Update DB for changed files
            now = datetime.now(timezone.utc)
            doc_map = {d.relative_path: d for d in new_docs}

            for analysis in changed_files:
                existing = await db.execute(
                    select(SourceFile).where(
                        SourceFile.project_id == project_id,
                        SourceFile.relative_path == analysis.relative_path,
                    )
                )
                sf = existing.scalar_one_or_none()
                doc = doc_map.get(analysis.relative_path)

                if sf:
                    sf.content_hash = analysis.file_hash
                    sf.line_count = analysis.line_count
                    sf.analysis_data = analysis.model_dump()
                    sf.last_analyzed_at = now
                    if doc:
                        sf.documentation_md = doc.full_markdown
                        sf.last_documented_at = now
                        sf.status = FileStatus.documented
                    else:
                        sf.status = FileStatus.analyzed
                else:
                    sf = SourceFile(
                        project_id=project_id,
                        relative_path=analysis.relative_path,
                        content_hash=analysis.file_hash,
                        line_count=analysis.line_count,
                        token_estimate=analysis.line_count * 4,
                        language=_detect_language(analysis.relative_path),
                        last_analyzed_at=now,
                        last_documented_at=now if doc else None,
                        analysis_data=analysis.model_dump(),
                        documentation_md=doc.full_markdown if doc else None,
                        status=FileStatus.documented if doc else FileStatus.analyzed,
                    )
                    db.add(sf)

            project.last_indexed_at = now
            project.file_count = len(all_analyses)
            await db.commit()
            logger.info("Incremental index complete for %s: %d files updated", project.name, len(changed_files))

    except Exception:
        logger.exception("Incremental index failed for project %s", project_id)
    finally:
        _running_tasks.pop(project_id, None)


def _detect_language(path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
        ".jsx": "javascript", ".java": "java", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp", ".h": "c",
        ".cs": "csharp", ".swift": "swift", ".kt": "kotlin", ".scala": "scala",
        ".r": "r", ".sql": "sql", ".sh": "shell", ".yml": "yaml", ".yaml": "yaml",
        ".json": "json", ".md": "markdown", ".html": "html", ".css": "css",
    }
    for ext, lang in ext_map.items():
        if path.endswith(ext):
            return lang
    return "unknown"
