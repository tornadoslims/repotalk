"""GitHub/GitLab webhook endpoints + file watcher management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_project
from server.models_db import Project
from server.schemas import UpdateLogEntry, WatcherConfig, WatcherStatus, WebhookPayload
from server.services import watcher

router = APIRouter(tags=["webhooks"])


@router.post("/api/hooks/github")
async def github_webhook(request: Request):
    """Handle GitHub push webhook."""
    payload = await request.json()
    result = await watcher.handle_github_webhook(payload)
    return result


@router.post("/api/hooks/gitlab")
async def gitlab_webhook(request: Request):
    """Handle GitLab push webhook."""
    payload = await request.json()
    result = await watcher.handle_gitlab_webhook(payload)
    return result


@router.get("/api/projects/{id}/watcher", response_model=WatcherStatus)
async def get_watcher_status(
    project: Project = Depends(get_project),
):
    w = watcher.get_watcher(project.id)
    if w:
        status = w.status
        return WatcherStatus(
            project_id=project.id,
            active=status["active"],
            watched_path=status["watched_path"],
            last_event_at=status["last_event_at"],
            events_since_start=status["events_since_start"],
        )
    return WatcherStatus(
        project_id=project.id,
        active=False,
        watched_path=project.source_path,
    )


@router.patch("/api/projects/{id}/watcher", response_model=WatcherStatus)
async def configure_watcher(
    body: WatcherConfig,
    project: Project = Depends(get_project),
):
    if body.active is True:
        debounce = body.debounce_seconds or 5.0
        w = watcher.start_watcher(project.id, project.source_path, debounce)
        status = w.status
        return WatcherStatus(
            project_id=project.id,
            active=True,
            watched_path=project.source_path,
        )
    elif body.active is False:
        watcher.stop_watcher(project.id)
        return WatcherStatus(
            project_id=project.id,
            active=False,
            watched_path=project.source_path,
        )

    # Just update debounce
    w = watcher.get_watcher(project.id)
    if w and body.debounce_seconds is not None:
        w.debounce_seconds = body.debounce_seconds
    return WatcherStatus(
        project_id=project.id,
        active=w.active if w else False,
        watched_path=project.source_path,
    )


@router.get("/api/projects/{id}/updates", response_model=list[UpdateLogEntry])
async def get_update_log(
    project: Project = Depends(get_project),
):
    w = watcher.get_watcher(project.id)
    if not w:
        return []
    return [
        UpdateLogEntry(
            timestamp=entry["timestamp"],
            event_type=entry["event_type"],
            path=entry.get("path"),
            details=entry.get("details", ""),
        )
        for entry in w.updates[-100:]  # Last 100 entries
    ]
