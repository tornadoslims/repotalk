"""Database engine and session management.

Supports SQLite (solo mode) and PostgreSQL (team mode) via DATABASE_URL env var.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _default_db_url() -> str:
    """Build default SQLite URL relative to the project root."""
    from repotalk.config import find_project_root
    root = find_project_root()
    db_path = root / "repotalk.db"
    return f"sqlite+aiosqlite:///{db_path}"


DATABASE_URL = os.getenv("DATABASE_URL") or _default_db_url()

# Convert postgres:// to postgresql+asyncpg:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    **({"connect_args": {"check_same_thread": False}} if _is_sqlite else {"pool_size": 20, "max_overflow": 10}),
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables (used in solo/dev mode)."""
    if _is_sqlite:
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async with engine.begin() as conn:
        from server.models_db import (  # noqa: F401 – ensure models registered
            AgentSession,
            Annotation,
            Conversation,
            DirectorySummaryRow,
            GraphEdgeRow,
            GraphNodeRow,
            Message,
            Project,
            SourceFile,
            User,
        )
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
