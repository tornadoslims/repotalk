"""Agent orchestration endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth import CurrentUser, get_current_user
from server.dependencies import get_db, get_project
from server.models_db import Project
from server.schemas import AgentRunRequest, AgentSessionOut
from server.services import agent_service

router = APIRouter(tags=["agents"])


@router.post("/api/projects/{id}/agents/run", response_model=AgentSessionOut, status_code=201)
async def spawn_agent(
    body: AgentRunRequest,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    session = await agent_service.spawn_agent(
        db=db,
        project=project,
        agent_type=body.agent_type,
        task_description=body.task_description,
        context=body.context,
        user_id=user.user_id,
        conversation_id=body.conversation_id,
    )
    return session


@router.get("/api/agents/{sessionId}", response_model=AgentSessionOut)
async def get_agent_status(
    sessionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await agent_service.get_agent_status(db, sessionId)
    if not session:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return session


@router.post("/api/agents/{sessionId}/approve", response_model=AgentSessionOut)
async def approve_agent(
    sessionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await agent_service.approve_agent(db, sessionId)
    if not session:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return session


@router.delete("/api/agents/{sessionId}", response_model=AgentSessionOut)
async def kill_agent(
    sessionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await agent_service.kill_agent(db, sessionId)
    if not session:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return session
