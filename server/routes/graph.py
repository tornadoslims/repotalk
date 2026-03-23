"""Graph query endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_project
from server.models_db import Project
from server.schemas import (
    GraphEdgeOut,
    GraphNodeOut,
    GraphOut,
    ImpactResult,
    MermaidOut,
    NodeDetail,
    SimilarNode,
    TraceResult,
)
from server.services import graph_service

router = APIRouter(prefix="/api/projects/{id}/graph", tags=["graph"])


@router.get("", response_model=GraphOut)
async def get_graph(
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    data = await graph_service.get_full_graph(db, project.id)
    return GraphOut(
        nodes=[GraphNodeOut.model_validate(n) for n in data["nodes"]],
        edges=[GraphEdgeOut.model_validate(e) for e in data["edges"]],
        stats=data["stats"],
    )


@router.get("/subgraph", response_model=GraphOut)
async def get_subgraph(
    node: str = Query(..., description="Qualified name of the center node"),
    depth: int = Query(2, ge=1, le=10),
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    data = await graph_service.get_subgraph(db, project.id, node, depth)
    return GraphOut(
        nodes=[GraphNodeOut.model_validate(n) for n in data["nodes"]],
        edges=[GraphEdgeOut.model_validate(e) for e in data["edges"]],
        stats=data["stats"],
    )


@router.get("/nodes", response_model=list[GraphNodeOut])
async def search_nodes(
    type: str | None = Query(None),
    search: str | None = Query(None),
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    nodes = await graph_service.search_nodes(db, project.id, type, search)
    return [GraphNodeOut.model_validate(n) for n in nodes]


@router.get("/node/{nodeId}", response_model=NodeDetail)
async def get_node(
    nodeId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    detail = await graph_service.get_node_detail(db, project.id, nodeId)
    if not detail:
        raise HTTPException(status_code=404, detail="Node not found")
    return NodeDetail(
        **GraphNodeOut.model_validate(detail["node"]).model_dump(),
        incoming_edges=[GraphEdgeOut.model_validate(e) for e in detail["incoming_edges"]],
        outgoing_edges=[GraphEdgeOut.model_validate(e) for e in detail["outgoing_edges"]],
    )


@router.get("/trace/{nodeId}", response_model=TraceResult)
async def trace_node(
    nodeId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    data = await graph_service.trace_calls(db, project.id, nodeId)
    return TraceResult(
        root_node_id=data["root_node_id"],
        nodes=[GraphNodeOut.model_validate(n) for n in data["nodes"]],
        edges=[GraphEdgeOut.model_validate(e) for e in data["edges"]],
        depth=data["depth"],
    )


@router.get("/impact/{nodeId}", response_model=ImpactResult)
async def impact_analysis(
    nodeId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    data = await graph_service.impact_analysis(db, project.id, nodeId)
    return ImpactResult(
        target_node_id=data["target_node_id"],
        affected_nodes=[GraphNodeOut.model_validate(n) for n in data["affected_nodes"]],
        affected_edges=[GraphEdgeOut.model_validate(e) for e in data["affected_edges"]],
        depth=data["depth"],
    )


@router.get("/similar/{nodeId}", response_model=list[SimilarNode])
async def find_similar(
    nodeId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    results = await graph_service.find_similar(db, project.id, nodeId)
    return [
        SimilarNode(
            node=GraphNodeOut.model_validate(r["node"]),
            similarity_score=r["similarity_score"],
        )
        for r in results
    ]


@router.get("/mermaid", response_model=MermaidOut)
async def mermaid_diagram(
    scope: str | None = Query(None, description="Filter by path prefix"),
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    data = await graph_service.generate_mermaid(db, project.id, scope)
    return MermaidOut(diagram=data["diagram"], node_count=data["node_count"])
