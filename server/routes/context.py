"""Context export for external LLM use."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_config, get_db, get_project
from server.models_db import Project
from server.schemas import ContextExportRequest, ContextExportResponse

router = APIRouter(prefix="/api/projects/{id}/context", tags=["context"])


@router.post("", response_model=ContextExportResponse)
async def export_context(
    body: ContextExportRequest,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    if not project.output_path:
        raise HTTPException(status_code=400, detail="Project not indexed yet")

    config = get_config()
    docs_dir = Path(project.output_path)

    # Use core retriever
    from repotalk.retriever import DocumentRetriever
    retriever = DocumentRetriever(config, docs_dir)
    contexts = retriever.retrieve_keyword(body.query, top_k=body.depth * 5)

    docs = []
    total_tokens = 0
    for ctx in contexts:
        token_est = len(ctx.content.split()) * 1.3  # rough token estimate
        if total_tokens + token_est > body.max_tokens:
            break
        docs.append({
            "source": ctx.source,
            "content": ctx.content,
            "relevance": ctx.relevance_score,
            "type": ctx.doc_type,
        })
        total_tokens += int(token_est)

    # Get source snippets for high-relevance matches
    source_snippets = []
    root = Path(project.source_path)
    for ctx in contexts[:3]:  # Top 3
        if ctx.doc_type == "file":
            src_path = root / ctx.source
            if src_path.is_file():
                try:
                    content = src_path.read_text(errors="replace")
                    snippet_tokens = len(content.split()) * 1.3
                    if total_tokens + snippet_tokens <= body.max_tokens:
                        source_snippets.append({
                            "path": ctx.source,
                            "content": content[:5000],  # cap individual files
                        })
                        total_tokens += int(min(snippet_tokens, 5000 * 1.3))
                except Exception:
                    pass

    # Get graph context if available
    graph_data = None
    try:
        from repotalk.graph import KnowledgeGraph
        from repotalk.output import get_output_dir
        graph = KnowledgeGraph.load(docs_dir)
        graph_data = graph.to_json()
        # Trim graph to relevant nodes only
        relevant_paths = {ctx.source for ctx in contexts}
        graph_data["nodes"] = [
            n for n in graph_data.get("nodes", [])
            if n.get("file_path") in relevant_paths or n.get("type") == "directory"
        ]
        relevant_ids = {n["id"] for n in graph_data["nodes"]}
        graph_data["edges"] = [
            e for e in graph_data.get("edges", [])
            if e.get("source") in relevant_ids and e.get("target") in relevant_ids
        ]
    except Exception:
        pass

    return ContextExportResponse(
        docs=docs,
        graph=graph_data,
        source_snippets=source_snippets,
        total_tokens=int(total_tokens),
    )
