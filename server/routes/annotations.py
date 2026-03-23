"""Annotation CRUD endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth import CurrentUser, get_current_user
from server.dependencies import get_db, get_project
from server.models_db import Annotation, AnnotationTargetType, Project
from server.schemas import AnnotationCreate, AnnotationOut

router = APIRouter(tags=["annotations"])


@router.get("/api/projects/{id}/annotations", response_model=list[AnnotationOut])
async def list_annotations(
    target: str | None = Query(None, description="Filter by target (e.g., 'file:auth.py')"),
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    query = select(Annotation).where(Annotation.project_id == project.id)

    if target:
        # Parse target filter: "type:id" format
        if ":" in target:
            target_type, target_id = target.split(":", 1)
            try:
                tt = AnnotationTargetType(target_type)
                query = query.where(
                    Annotation.target_type == tt,
                    Annotation.target_id == target_id,
                )
            except ValueError:
                query = query.where(Annotation.target_id.ilike(f"%{target}%"))
        else:
            query = query.where(Annotation.target_id.ilike(f"%{target}%"))

    query = query.order_by(Annotation.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/api/projects/{id}/annotations", response_model=AnnotationOut, status_code=201)
async def create_annotation(
    body: AnnotationCreate,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        target_type = AnnotationTargetType(body.target_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_type: {body.target_type}. Must be one of: {[t.value for t in AnnotationTargetType]}",
        )

    ann = Annotation(
        project_id=project.id,
        user_id=user.user_id,
        target_type=target_type,
        target_id=body.target_id,
        content=body.content,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.delete("/api/annotations/{id}", status_code=204)
async def delete_annotation(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Annotation).where(Annotation.id == id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")
    await db.delete(ann)
    await db.commit()
