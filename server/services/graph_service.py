"""Graph query service — trace, impact, subgraph, similarity."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models_db import GraphEdgeRow, GraphNodeRow, EdgeTypeEnum

logger = logging.getLogger("repotalk.graph_service")


async def get_full_graph(db: AsyncSession, project_id: uuid.UUID) -> dict[str, Any]:
    nodes_result = await db.execute(
        select(GraphNodeRow).where(GraphNodeRow.project_id == project_id)
    )
    edges_result = await db.execute(
        select(GraphEdgeRow).where(GraphEdgeRow.project_id == project_id)
    )
    nodes = nodes_result.scalars().all()
    edges = edges_result.scalars().all()

    node_counts: dict[str, int] = {}
    for n in nodes:
        t = n.node_type.value if hasattr(n.node_type, "value") else str(n.node_type)
        node_counts[t] = node_counts.get(t, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            **node_counts,
        },
    }


async def get_subgraph(
    db: AsyncSession, project_id: uuid.UUID, node_qualified_name: str, depth: int = 2
) -> dict[str, Any]:
    """Get a local subgraph around a node up to given depth."""
    # Find the root node
    result = await db.execute(
        select(GraphNodeRow).where(
            GraphNodeRow.project_id == project_id,
            GraphNodeRow.qualified_name == node_qualified_name,
        )
    )
    root = result.scalar_one_or_none()
    if not root:
        return {"nodes": [], "edges": [], "stats": {"total_nodes": 0, "total_edges": 0}}

    visited_ids: set[uuid.UUID] = {root.id}
    frontier: set[uuid.UUID] = {root.id}
    all_edges: list[GraphEdgeRow] = []

    for _ in range(depth):
        if not frontier:
            break
        edges_result = await db.execute(
            select(GraphEdgeRow).where(
                GraphEdgeRow.project_id == project_id,
                or_(
                    GraphEdgeRow.source_node_id.in_(frontier),
                    GraphEdgeRow.target_node_id.in_(frontier),
                ),
            )
        )
        edges = edges_result.scalars().all()
        all_edges.extend(edges)

        new_frontier: set[uuid.UUID] = set()
        for e in edges:
            if e.source_node_id not in visited_ids:
                new_frontier.add(e.source_node_id)
                visited_ids.add(e.source_node_id)
            if e.target_node_id not in visited_ids:
                new_frontier.add(e.target_node_id)
                visited_ids.add(e.target_node_id)
        frontier = new_frontier

    nodes_result = await db.execute(
        select(GraphNodeRow).where(GraphNodeRow.id.in_(visited_ids))
    )
    nodes = nodes_result.scalars().all()

    # Deduplicate edges
    seen_edge_ids: set[uuid.UUID] = set()
    unique_edges = []
    for e in all_edges:
        if e.id not in seen_edge_ids:
            seen_edge_ids.add(e.id)
            unique_edges.append(e)

    return {
        "nodes": nodes,
        "edges": unique_edges,
        "stats": {"total_nodes": len(nodes), "total_edges": len(unique_edges)},
    }


async def search_nodes(
    db: AsyncSession, project_id: uuid.UUID, node_type: str | None = None, search: str | None = None
) -> list[GraphNodeRow]:
    query = select(GraphNodeRow).where(GraphNodeRow.project_id == project_id)
    if node_type:
        try:
            from server.models_db import NodeType
            nt = NodeType(node_type)
            query = query.where(GraphNodeRow.node_type == nt)
        except ValueError:
            pass
    if search:
        query = query.where(
            or_(
                GraphNodeRow.qualified_name.ilike(f"%{search}%"),
                GraphNodeRow.display_name.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(query.limit(200))
    return list(result.scalars().all())


async def get_node_detail(
    db: AsyncSession, project_id: uuid.UUID, node_id: uuid.UUID
) -> dict[str, Any] | None:
    node_result = await db.execute(
        select(GraphNodeRow).where(
            GraphNodeRow.id == node_id,
            GraphNodeRow.project_id == project_id,
        )
    )
    node = node_result.scalar_one_or_none()
    if not node:
        return None

    incoming = await db.execute(
        select(GraphEdgeRow).where(
            GraphEdgeRow.target_node_id == node_id,
            GraphEdgeRow.project_id == project_id,
        )
    )
    outgoing = await db.execute(
        select(GraphEdgeRow).where(
            GraphEdgeRow.source_node_id == node_id,
            GraphEdgeRow.project_id == project_id,
        )
    )

    return {
        "node": node,
        "incoming_edges": list(incoming.scalars().all()),
        "outgoing_edges": list(outgoing.scalars().all()),
    }


async def trace_calls(
    db: AsyncSession, project_id: uuid.UUID, node_id: uuid.UUID, max_depth: int = 10
) -> dict[str, Any]:
    """Follow calls edges recursively from a node (forward call trace)."""
    visited: set[uuid.UUID] = {node_id}
    frontier: set[uuid.UUID] = {node_id}
    all_edges: list[GraphEdgeRow] = []
    depth = 0

    while frontier and depth < max_depth:
        edges_result = await db.execute(
            select(GraphEdgeRow).where(
                GraphEdgeRow.project_id == project_id,
                GraphEdgeRow.source_node_id.in_(frontier),
                GraphEdgeRow.edge_type == EdgeTypeEnum.calls,
            )
        )
        edges = edges_result.scalars().all()
        if not edges:
            break
        all_edges.extend(edges)

        new_frontier: set[uuid.UUID] = set()
        for e in edges:
            if e.target_node_id not in visited:
                visited.add(e.target_node_id)
                new_frontier.add(e.target_node_id)
        frontier = new_frontier
        depth += 1

    nodes_result = await db.execute(
        select(GraphNodeRow).where(GraphNodeRow.id.in_(visited))
    )
    return {
        "root_node_id": node_id,
        "nodes": list(nodes_result.scalars().all()),
        "edges": all_edges,
        "depth": depth,
    }


async def impact_analysis(
    db: AsyncSession, project_id: uuid.UUID, node_id: uuid.UUID, max_depth: int = 10
) -> dict[str, Any]:
    """Reverse trace — what depends on this node."""
    visited: set[uuid.UUID] = {node_id}
    frontier: set[uuid.UUID] = {node_id}
    all_edges: list[GraphEdgeRow] = []
    depth = 0

    while frontier and depth < max_depth:
        edges_result = await db.execute(
            select(GraphEdgeRow).where(
                GraphEdgeRow.project_id == project_id,
                GraphEdgeRow.target_node_id.in_(frontier),
            )
        )
        edges = edges_result.scalars().all()
        if not edges:
            break
        all_edges.extend(edges)

        new_frontier: set[uuid.UUID] = set()
        for e in edges:
            if e.source_node_id not in visited:
                visited.add(e.source_node_id)
                new_frontier.add(e.source_node_id)
        frontier = new_frontier
        depth += 1

    nodes_result = await db.execute(
        select(GraphNodeRow).where(GraphNodeRow.id.in_(visited))
    )
    return {
        "target_node_id": node_id,
        "affected_nodes": list(nodes_result.scalars().all()),
        "affected_edges": all_edges,
        "depth": depth,
    }


async def find_similar(
    db: AsyncSession, project_id: uuid.UUID, node_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Find structurally similar nodes based on type, complexity, and edge patterns."""
    node_result = await db.execute(
        select(GraphNodeRow).where(
            GraphNodeRow.id == node_id,
            GraphNodeRow.project_id == project_id,
        )
    )
    node = node_result.scalar_one_or_none()
    if not node:
        return []

    # Find nodes of the same type
    candidates_result = await db.execute(
        select(GraphNodeRow).where(
            GraphNodeRow.project_id == project_id,
            GraphNodeRow.node_type == node.node_type,
            GraphNodeRow.id != node_id,
        ).limit(100)
    )
    candidates = candidates_result.scalars().all()

    # Score similarity based on available attributes
    results = []
    node_complexity = node.complexity or 1
    node_name_parts = set(node.display_name.lower().replace("_", " ").split())

    for c in candidates:
        score = 0.0
        # Complexity similarity
        c_complexity = c.complexity or 1
        if node_complexity > 0 and c_complexity > 0:
            ratio = min(node_complexity, c_complexity) / max(node_complexity, c_complexity)
            score += ratio * 0.4

        # Name similarity (Jaccard on name parts)
        c_name_parts = set(c.display_name.lower().replace("_", " ").split())
        if node_name_parts and c_name_parts:
            intersection = len(node_name_parts & c_name_parts)
            union = len(node_name_parts | c_name_parts)
            score += (intersection / union) * 0.4 if union > 0 else 0

        # Signature similarity
        if node.signature and c.signature:
            # Simple check: same number of parameters
            node_params = node.signature.count(",") + 1
            c_params = c.signature.count(",") + 1
            param_ratio = min(node_params, c_params) / max(node_params, c_params)
            score += param_ratio * 0.2

        if score > 0.2:
            results.append({"node": c, "similarity_score": round(score, 3)})

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:20]


async def generate_mermaid(
    db: AsyncSession, project_id: uuid.UUID, scope: str | None = None
) -> dict[str, Any]:
    """Generate Mermaid diagram for the project graph or a scoped subset."""
    query = select(GraphNodeRow).where(GraphNodeRow.project_id == project_id)
    if scope:
        query = query.where(GraphNodeRow.qualified_name.ilike(f"{scope}%"))
    nodes_result = await db.execute(query.limit(80))
    nodes = nodes_result.scalars().all()
    node_ids = {n.id for n in nodes}

    edges_result = await db.execute(
        select(GraphEdgeRow).where(
            GraphEdgeRow.project_id == project_id,
            GraphEdgeRow.source_node_id.in_(node_ids),
            GraphEdgeRow.target_node_id.in_(node_ids),
        )
    )
    edges = edges_result.scalars().all()

    # Build Mermaid
    lines = ["graph TD"]
    node_labels: dict[uuid.UUID, str] = {}
    for n in nodes:
        safe_id = str(n.id).replace("-", "")[:12]
        label = n.display_name.replace('"', "'")
        node_labels[n.id] = safe_id
        node_type = n.node_type.value if hasattr(n.node_type, "value") else str(n.node_type)
        if node_type == "file":
            lines.append(f'    {safe_id}["{label}"]')
        elif node_type == "function" or node_type == "method":
            lines.append(f'    {safe_id}("{label}")')
        elif node_type in ("class", "class_"):
            lines.append(f'    {safe_id}[["{label}"]]')
        else:
            lines.append(f'    {safe_id}("{label}")')

    for e in edges:
        src = node_labels.get(e.source_node_id)
        tgt = node_labels.get(e.target_node_id)
        if src and tgt:
            edge_label = e.edge_type.value if hasattr(e.edge_type, "value") else str(e.edge_type)
            lines.append(f"    {src} -->|{edge_label}| {tgt}")

    diagram = "\n".join(lines)
    return {"diagram": diagram, "node_count": len(nodes)}
