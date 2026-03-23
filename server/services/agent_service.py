"""Agent service — coding agent lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.database import async_session
from server.models_db import AgentSession, AgentStatus, Project

logger = logging.getLogger("repotalk.agent_service")

_running_agents: dict[uuid.UUID, asyncio.Task] = {}


async def spawn_agent(
    db: AsyncSession,
    project: Project,
    agent_type: str,
    task_description: str,
    context: dict[str, Any] | None = None,
    user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> AgentSession:
    """Spawn a new agent session and start it in the background."""
    session = AgentSession(
        project_id=project.id,
        user_id=user_id,
        conversation_id=conversation_id,
        agent_type=agent_type,
        task_description=task_description,
        context_provided=context,
        status=AgentStatus.pending,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Launch background task
    task = asyncio.create_task(_run_agent(session.id, project, agent_type, task_description, context))
    _running_agents[session.id] = task

    return session


async def get_agent_status(db: AsyncSession, session_id: uuid.UUID) -> AgentSession | None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    return result.scalar_one_or_none()


async def approve_agent(db: AsyncSession, session_id: uuid.UUID) -> AgentSession | None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return None
    if session.status == AgentStatus.awaiting_approval:
        session.status = AgentStatus.approved
        await db.commit()
        await db.refresh(session)
    return session


async def kill_agent(db: AsyncSession, session_id: uuid.UUID) -> AgentSession | None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return None

    # Cancel the running task
    task = _running_agents.pop(session_id, None)
    if task and not task.done():
        task.cancel()

    session.status = AgentStatus.killed
    session.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


async def _run_agent(
    session_id: uuid.UUID,
    project: Project,
    agent_type: str,
    task_description: str,
    context: dict[str, Any] | None,
) -> None:
    """Execute the agent task. Currently a framework stub that can be extended."""
    try:
        async with async_session() as db:
            result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session:
                return

            session.status = AgentStatus.running
            await db.commit()

            # Agent execution logic — this is where a real coding agent would:
            # 1. Create a git branch
            # 2. Analyze the codebase using the knowledge graph
            # 3. Make code changes
            # 4. Run tests
            # 5. Create a PR
            #
            # For now, we simulate the workflow
            branch_name = f"repotalk/agent-{session_id.hex[:8]}"

            logger.info("Agent %s running task: %s", session_id, task_description)

            # Simulate work
            await asyncio.sleep(1)

            # Move to awaiting approval
            session.status = AgentStatus.awaiting_approval
            session.branch_name = branch_name
            session.result_summary = f"Agent analyzed the task and prepared changes on branch {branch_name}."
            await db.commit()

            # Wait for approval or cancellation
            for _ in range(600):  # 10 minute timeout
                await asyncio.sleep(1)
                await db.refresh(session)
                if session.status == AgentStatus.approved:
                    session.status = AgentStatus.completed
                    session.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    break
                if session.status in (AgentStatus.killed, AgentStatus.failed):
                    break
            else:
                # Timeout
                session.status = AgentStatus.failed
                session.result_summary = "Agent timed out waiting for approval."
                session.completed_at = datetime.now(timezone.utc)
                await db.commit()

    except asyncio.CancelledError:
        logger.info("Agent %s was cancelled", session_id)
    except Exception:
        logger.exception("Agent %s failed", session_id)
        try:
            async with async_session() as db:
                result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
                session = result.scalar_one_or_none()
                if session:
                    session.status = AgentStatus.failed
                    session.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception:
            pass
    finally:
        _running_agents.pop(session_id, None)
