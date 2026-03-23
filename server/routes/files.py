"""File listing and source endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_project
from server.models_db import Project, SourceFile
from server.schemas import SourceFileDetail, SourceFileOut

router = APIRouter(prefix="/api/projects/{id}/files", tags=["files"])


@router.get("", response_model=list[SourceFileOut])
async def list_files(
    status: str | None = Query(None, description="Filter by status"),
    language: str | None = Query(None),
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    query = select(SourceFile).where(SourceFile.project_id == project.id)
    if status:
        query = query.where(SourceFile.status == status)
    if language:
        query = query.where(SourceFile.language == language)
    query = query.order_by(SourceFile.relative_path)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{fileId}", response_model=SourceFileDetail)
async def get_file(
    fileId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SourceFile).where(
            SourceFile.id == fileId,
            SourceFile.project_id == project.id,
        )
    )
    sf = result.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="File not found")
    return sf


@router.get("/{fileId}/source", response_class=PlainTextResponse)
async def get_source(
    fileId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SourceFile).where(
            SourceFile.id == fileId,
            SourceFile.project_id == project.id,
        )
    )
    sf = result.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="File not found")

    source_path = Path(project.source_path) / sf.relative_path
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    return PlainTextResponse(source_path.read_text(errors="replace"))


@router.get("/{fileId}/doc", response_model=dict)
async def get_file_doc(
    fileId: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SourceFile).where(
            SourceFile.id == fileId,
            SourceFile.project_id == project.id,
        )
    )
    sf = result.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="File not found")
    if not sf.documentation_md:
        raise HTTPException(status_code=404, detail="Documentation not generated yet")

    return {
        "file_id": str(sf.id),
        "relative_path": sf.relative_path,
        "documentation": sf.documentation_md,
    }
