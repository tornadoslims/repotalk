"""Documentation tree and search endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_project
from server.models_db import DirectorySummaryRow, Project, SourceFile
from server.schemas import DocOut, DocSearchResult, DocTreeNode

router = APIRouter(prefix="/api/projects/{id}/docs", tags=["docs"])


@router.get("/tree", response_model=list[DocTreeNode])
async def get_doc_tree(
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    """Build the documentation tree structure."""
    # Get all files
    files_result = await db.execute(
        select(SourceFile).where(SourceFile.project_id == project.id).order_by(SourceFile.relative_path)
    )
    files = files_result.scalars().all()

    # Get directory summaries
    dirs_result = await db.execute(
        select(DirectorySummaryRow).where(DirectorySummaryRow.project_id == project.id)
    )
    dir_summaries = {d.relative_path: d for d in dirs_result.scalars().all()}

    # Build tree
    root_children: dict[str, DocTreeNode] = {}

    for sf in files:
        parts = Path(sf.relative_path).parts
        current_level = root_children

        for i, part in enumerate(parts):
            path_so_far = "/".join(parts[: i + 1])

            if i == len(parts) - 1:
                # Leaf file
                node = DocTreeNode(
                    path=sf.relative_path,
                    name=part,
                    type="file",
                    has_doc=sf.documentation_md is not None,
                )
                current_level[path_so_far] = node
            else:
                # Directory
                if path_so_far not in current_level:
                    has_summary = path_so_far in dir_summaries
                    dir_node = DocTreeNode(
                        path=path_so_far,
                        name=part,
                        type="directory",
                        has_doc=has_summary,
                    )
                    current_level[path_so_far] = dir_node
                current_level = {
                    c.path: c
                    for c in current_level[path_so_far].children
                }
                # We need to re-add children properly
                parent = _find_or_create_dir(root_children, parts[: i + 1], dir_summaries)
                current_level = {c.path: c for c in parent.children}

    return list(root_children.values())


def _find_or_create_dir(
    level: dict[str, DocTreeNode], path_parts: tuple | list, dir_summaries: dict
) -> DocTreeNode:
    path_so_far = "/".join(path_parts)
    if path_so_far in level:
        return level[path_so_far]

    has_summary = path_so_far in dir_summaries
    node = DocTreeNode(
        path=path_so_far,
        name=path_parts[-1],
        type="directory",
        has_doc=has_summary,
    )
    level[path_so_far] = node
    return node


@router.get("/architecture", response_model=DocOut)
async def get_architecture_doc(
    project: Project = Depends(get_project),
):
    """Get top-level architecture documentation (PROJECT_OVERVIEW.md)."""
    if not project.output_path:
        raise HTTPException(status_code=404, detail="Project not indexed yet")

    overview_path = Path(project.output_path) / "PROJECT_OVERVIEW.md"
    if not overview_path.is_file():
        raise HTTPException(status_code=404, detail="Architecture doc not generated")

    return DocOut(
        path="PROJECT_OVERVIEW.md",
        content=overview_path.read_text(errors="replace"),
        doc_type="project",
    )


@router.get("/search", response_model=list[DocSearchResult])
async def search_docs(
    q: str = Query(..., min_length=1, description="Search query"),
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search within documentation."""
    query_lower = q.lower()

    # Search file docs
    files_result = await db.execute(
        select(SourceFile).where(
            SourceFile.project_id == project.id,
            SourceFile.documentation_md.isnot(None),
        )
    )
    files = files_result.scalars().all()

    results = []
    for sf in files:
        if not sf.documentation_md:
            continue
        doc_lower = sf.documentation_md.lower()
        if query_lower in doc_lower:
            # Find snippet around match
            idx = doc_lower.index(query_lower)
            start = max(0, idx - 100)
            end = min(len(sf.documentation_md), idx + len(q) + 200)
            snippet = sf.documentation_md[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(sf.documentation_md):
                snippet = snippet + "..."

            # Simple relevance scoring: count occurrences
            count = doc_lower.count(query_lower)
            relevance = min(1.0, count / 10.0)

            results.append(DocSearchResult(
                path=sf.relative_path,
                snippet=snippet,
                relevance=relevance,
                doc_type="file",
            ))

    # Search directory summaries
    dirs_result = await db.execute(
        select(DirectorySummaryRow).where(
            DirectorySummaryRow.project_id == project.id,
            DirectorySummaryRow.summary_md.isnot(None),
        )
    )
    for ds in dirs_result.scalars().all():
        if not ds.summary_md:
            continue
        md_lower = ds.summary_md.lower()
        if query_lower in md_lower:
            idx = md_lower.index(query_lower)
            start = max(0, idx - 100)
            end = min(len(ds.summary_md), idx + len(q) + 200)
            snippet = ds.summary_md[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(ds.summary_md):
                snippet = snippet + "..."

            count = md_lower.count(query_lower)
            results.append(DocSearchResult(
                path=ds.relative_path,
                snippet=snippet,
                relevance=min(1.0, count / 10.0),
                doc_type="directory",
            ))

    results.sort(key=lambda x: x.relevance, reverse=True)
    return results[:50]


@router.get("/{path:path}", response_model=DocOut)
async def get_doc_at_path(
    path: str,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    """Get documentation for a specific path (file or directory)."""
    # Check if it's a file doc
    file_result = await db.execute(
        select(SourceFile).where(
            SourceFile.project_id == project.id,
            SourceFile.relative_path == path,
        )
    )
    sf = file_result.scalar_one_or_none()
    if sf and sf.documentation_md:
        return DocOut(path=path, content=sf.documentation_md, doc_type="file")

    # Check if it's a directory summary
    dir_result = await db.execute(
        select(DirectorySummaryRow).where(
            DirectorySummaryRow.project_id == project.id,
            DirectorySummaryRow.relative_path == path,
        )
    )
    ds = dir_result.scalar_one_or_none()
    if ds and ds.summary_md:
        return DocOut(path=path, content=ds.summary_md, doc_type="directory")

    raise HTTPException(status_code=404, detail=f"No documentation found at path: {path}")
