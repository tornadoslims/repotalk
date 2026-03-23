"""FastAPI dependencies for database sessions, project lookup, and shared clients."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.database import get_session
from server.models_db import Project

# Shared LLM client instance (initialized during lifespan)
_llm_client: Any = None
_config: Any = None


def set_shared_config(config: Any) -> None:
    global _config
    _config = config


def set_shared_llm_client(client: Any) -> None:
    global _llm_client
    _llm_client = client


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async for session in get_session():
        yield session


async def get_project(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Project:
    result = await db.execute(select(Project).where(Project.id == id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {id} not found")
    return project


def get_llm_client():
    if _llm_client is None:
        raise HTTPException(status_code=503, detail="LLM client not initialized")
    return _llm_client


def get_config():
    if _config is None:
        raise HTTPException(status_code=503, detail="Config not initialized")
    return _config
