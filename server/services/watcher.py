"""File system watcher using watchdog + webhook handler."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("repotalk.watcher")


class ProjectWatcher:
    """Watches a project directory for file changes and triggers incremental indexing."""

    def __init__(self, project_id: uuid.UUID, source_path: str, debounce_seconds: float = 5.0):
        self.project_id = project_id
        self.source_path = source_path
        self.debounce_seconds = debounce_seconds
        self.active = False
        self._observer: Any = None
        self._pending_changes: set[str] = set()
        self._debounce_task: asyncio.Task | None = None
        self._event_count = 0
        self._last_event_at: datetime | None = None
        self._update_log: list[dict[str, Any]] = []

    def start(self) -> None:
        if self.active:
            return
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent

            watcher = self

            class _Handler(FileSystemEventHandler):
                def on_any_event(self, event: FileSystemEvent) -> None:
                    if event.is_directory:
                        return
                    src = getattr(event, "src_path", "")
                    if any(p in src for p in ("__pycache__", ".git", ".repotalk")):
                        return
                    watcher._on_change(src, event.event_type)

            self._observer = Observer()
            self._observer.schedule(_Handler(), self.source_path, recursive=True)
            self._observer.start()
            self.active = True
            logger.info("Watcher started for project %s at %s", self.project_id, self.source_path)

        except ImportError:
            logger.warning("watchdog not installed — file watching disabled")
        except Exception:
            logger.exception("Failed to start watcher for %s", self.source_path)

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self.active = False
        logger.info("Watcher stopped for project %s", self.project_id)

    def _on_change(self, path: str, event_type: str) -> None:
        self._event_count += 1
        self._last_event_at = datetime.now(timezone.utc)
        self._pending_changes.add(path)
        self._update_log.append({
            "timestamp": self._last_event_at.isoformat(),
            "event_type": event_type,
            "path": path,
        })
        # Keep log bounded
        if len(self._update_log) > 1000:
            self._update_log = self._update_log[-500:]

        # Debounce: schedule incremental index
        try:
            loop = asyncio.get_event_loop()
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()
            self._debounce_task = loop.create_task(self._debounced_index())
        except RuntimeError:
            pass

    async def _debounced_index(self) -> None:
        await asyncio.sleep(self.debounce_seconds)
        changed = list(self._pending_changes)
        self._pending_changes.clear()
        if changed:
            logger.info("Triggering incremental index for %d changed files in project %s",
                        len(changed), self.project_id)
            from server.services.indexing import run_incremental_index
            from server.dependencies import get_config, get_llm_client
            try:
                config = get_config()
                llm_client = get_llm_client()
                await run_incremental_index(self.project_id, config, llm_client)
            except Exception:
                logger.exception("Debounced incremental index failed")

    @property
    def status(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "active": self.active,
            "watched_path": self.source_path,
            "last_event_at": self._last_event_at.isoformat() if self._last_event_at else None,
            "events_since_start": self._event_count,
        }

    @property
    def updates(self) -> list[dict[str, Any]]:
        return list(self._update_log)


# Global watcher registry
_watchers: dict[uuid.UUID, ProjectWatcher] = {}


def get_watcher(project_id: uuid.UUID) -> ProjectWatcher | None:
    return _watchers.get(project_id)


def start_watcher(project_id: uuid.UUID, source_path: str, debounce_seconds: float = 5.0) -> ProjectWatcher:
    existing = _watchers.get(project_id)
    if existing:
        existing.stop()
    w = ProjectWatcher(project_id, source_path, debounce_seconds)
    w.start()
    _watchers[project_id] = w
    return w


def stop_watcher(project_id: uuid.UUID) -> None:
    w = _watchers.pop(project_id, None)
    if w:
        w.stop()


def stop_all_watchers() -> None:
    for w in _watchers.values():
        w.stop()
    _watchers.clear()


async def handle_github_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle GitHub push webhook — find matching project and trigger index."""
    repo_url = payload.get("repository", {}).get("clone_url", "")
    ref = payload.get("ref", "")
    commits = payload.get("commits", [])

    if not commits:
        return {"status": "ignored", "reason": "no commits"}

    changed_files = set()
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        changed_files.update(commit.get("removed", []))

    logger.info("GitHub webhook: %s ref=%s, %d files changed", repo_url, ref, len(changed_files))

    # Find matching project and trigger incremental index
    from sqlalchemy import select
    from server.database import async_session
    from server.models_db import Project

    async with async_session() as db:
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        triggered = []
        for p in projects:
            if repo_url and repo_url in (p.source_path, p.config.get("repo_url", "") if p.config else ""):
                from server.services.indexing import run_incremental_index
                from server.dependencies import get_config, get_llm_client
                try:
                    config = get_config()
                    llm_client = get_llm_client()
                    asyncio.create_task(run_incremental_index(p.id, config, llm_client))
                    triggered.append(str(p.id))
                except Exception:
                    pass

    return {"status": "ok", "triggered_projects": triggered, "changed_files": len(changed_files)}


async def handle_gitlab_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle GitLab push webhook."""
    project_data = payload.get("project", {})
    repo_url = project_data.get("git_http_url", "")
    ref = payload.get("ref", "")
    commits = payload.get("commits", [])

    if not commits:
        return {"status": "ignored", "reason": "no commits"}

    changed_files = set()
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        changed_files.update(commit.get("removed", []))

    logger.info("GitLab webhook: %s ref=%s, %d files changed", repo_url, ref, len(changed_files))

    from sqlalchemy import select
    from server.database import async_session
    from server.models_db import Project

    async with async_session() as db:
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        triggered = []
        for p in projects:
            if repo_url and repo_url in (p.source_path, p.config.get("repo_url", "") if p.config else ""):
                from server.services.indexing import run_incremental_index
                from server.dependencies import get_config, get_llm_client
                try:
                    config = get_config()
                    llm_client = get_llm_client()
                    asyncio.create_task(run_incremental_index(p.id, config, llm_client))
                    triggered.append(str(p.id))
                except Exception:
                    pass

    return {"status": "ok", "triggered_projects": triggered, "changed_files": len(changed_files)}
