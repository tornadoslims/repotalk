"""Project CRUD + indexing endpoints."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth import CurrentUser, get_current_user
from server.dependencies import get_config, get_db, get_llm_client, get_project
from server.models_db import Annotation, Conversation, Project
from server.schemas import IndexStatus, ProjectCreate, ProjectOut, ProjectStats, ProjectUpdate
from server.services import indexing

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    source = Path(body.source_path)
    if not source.is_dir():
        raise HTTPException(status_code=400, detail=f"Source path does not exist or is not a directory: {body.source_path}")

    project = Project(
        name=body.name,
        source_path=str(source.resolve()),
        config=body.config,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{id}", response_model=ProjectStats)
async def get_project_detail(
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    conv_count = await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.project_id == project.id)
    )
    ann_count = await db.execute(
        select(func.count()).select_from(Annotation).where(Annotation.project_id == project.id)
    )
    return ProjectStats(
        id=project.id,
        name=project.name,
        source_path=project.source_path,
        output_path=project.output_path,
        config=project.config,
        last_indexed_at=project.last_indexed_at,
        file_count=project.file_count,
        graph_node_count=project.graph_node_count,
        graph_edge_count=project.graph_edge_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
        conversation_count=conv_count.scalar() or 0,
        annotation_count=ann_count.scalar() or 0,
    )


@router.patch("/{id}", response_model=ProjectOut)
async def update_project(
    body: ProjectUpdate,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    if body.name is not None:
        project.name = body.name
    if body.config is not None:
        project.config = body.config
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{id}", status_code=204)
async def delete_project(
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    from server.services.watcher import stop_watcher
    stop_watcher(project.id)
    await db.delete(project)
    await db.commit()


@router.post("/{id}/index", response_model=IndexStatus)
async def full_index(
    project: Project = Depends(get_project),
):
    existing = indexing.get_task(project.id)
    if existing and not existing.done():
        return IndexStatus(
            project_id=project.id,
            status="running",
            message="Indexing already in progress",
        )

    config = get_config()
    llm_client = get_llm_client()
    task = asyncio.create_task(indexing.run_full_index(project.id, config, llm_client))
    return IndexStatus(
        project_id=project.id,
        status="started",
        task_id=str(id(task)),
        message="Full indexing started",
    )


@router.get("/{id}/index-status", response_model=IndexStatus)
async def get_index_status(
    project: Project = Depends(get_project),
):
    existing = indexing.get_task(project.id)
    if existing and not existing.done():
        return IndexStatus(
            project_id=project.id,
            status="running",
            message="Indexing in progress",
        )
    if project.last_indexed_at:
        return IndexStatus(
            project_id=project.id,
            status="completed",
            message=f"Last indexed: {project.last_indexed_at.isoformat()}",
        )
    return IndexStatus(
        project_id=project.id,
        status="idle",
        message="Not yet indexed",
    )


@router.post("/{id}/index/incremental", response_model=IndexStatus)
async def incremental_index(
    project: Project = Depends(get_project),
):
    existing = indexing.get_task(project.id)
    if existing and not existing.done():
        return IndexStatus(
            project_id=project.id,
            status="running",
            message="Indexing already in progress",
        )

    config = get_config()
    llm_client = get_llm_client()
    task = asyncio.create_task(indexing.run_incremental_index(project.id, config, llm_client))
    return IndexStatus(
        project_id=project.id,
        status="started",
        task_id=str(id(task)),
        message="Incremental indexing started",
    )
