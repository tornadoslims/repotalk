"""RepoTalk FastAPI server — main application entry point.

Start with:
    python -m server.main
    uvicorn server.main:app --reload
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.database import init_db
from server.dependencies import set_shared_config, set_shared_llm_client
from server.schemas import HealthOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("repotalk.server")


# --- WebSocket manager for real-time updates ---

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel: str = "global"):
        await ws.accept()
        self._connections.setdefault(channel, []).append(ws)

    def disconnect(self, ws: WebSocket, channel: str = "global"):
        conns = self._connections.get(channel, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, channel: str, message: dict[str, Any]):
        data = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in self._connections.get(channel, []):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)

    async def send_to_project(self, project_id: uuid.UUID, event: str, data: dict[str, Any]):
        await self.broadcast(f"project:{project_id}", {"event": event, **data})


ws_manager = ConnectionManager()


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting RepoTalk server...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Load config from project root (where pyproject.toml lives)
    from repotalk.config import load_config, find_project_root
    project_root = find_project_root()
    config = load_config(target_path=project_root)
    set_shared_config(config)
    logger.info("Config loaded from %s (chat model: %s)", project_root, config.models.chat)

    # Initialize LLM client
    from repotalk.llm_client import LLMClient
    llm_client = LLMClient(config)
    set_shared_llm_client(llm_client)
    logger.info("LLM client initialized")

    # Store on app state for WebSocket access
    app.state.ws_manager = ws_manager

    yield

    # Shutdown
    logger.info("Shutting down RepoTalk server...")
    from server.services.watcher import stop_all_watchers
    stop_all_watchers()
    logger.info("All watchers stopped")


# --- App ---

app = FastAPI(
    title="RepoTalk API",
    description="AI-powered codebase intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        os.getenv("CORS_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---

@app.get("/health", response_model=HealthOut, tags=["health"])
async def health():
    return HealthOut(status="ok", version="0.1.0", database="connected")


# --- Mount routes ---

from server.routes.projects import router as projects_router
from server.routes.graph import router as graph_router
from server.routes.files import router as files_router
from server.routes.docs import router as docs_router
from server.routes.chat import router as chat_router
from server.routes.context import router as context_router
from server.routes.annotations import router as annotations_router
from server.routes.agents import router as agents_router
from server.routes.webhooks import router as webhooks_router
from server.routes.settings import router as settings_router
from server.routes.users import router as users_router

app.include_router(projects_router)
app.include_router(graph_router)
app.include_router(files_router)
app.include_router(docs_router)
app.include_router(chat_router)
app.include_router(context_router)
app.include_router(annotations_router)
app.include_router(agents_router)
app.include_router(webhooks_router)
app.include_router(settings_router)
app.include_router(users_router)


# --- WebSocket endpoints ---

@app.websocket("/ws")
async def websocket_global(ws: WebSocket):
    """Global WebSocket for server-wide events."""
    await ws_manager.connect(ws, "global")
    try:
        while True:
            data = await ws.receive_text()
            # Client can subscribe to project channels
            try:
                msg = json.loads(data)
                if msg.get("action") == "subscribe" and msg.get("project_id"):
                    channel = f"project:{msg['project_id']}"
                    await ws_manager.connect(ws, channel)
                    await ws.send_text(json.dumps({"event": "subscribed", "channel": channel}))
                elif msg.get("action") == "unsubscribe" and msg.get("project_id"):
                    channel = f"project:{msg['project_id']}"
                    ws_manager.disconnect(ws, channel)
                    await ws.send_text(json.dumps({"event": "unsubscribed", "channel": channel}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, "global")


@app.websocket("/ws/project/{project_id}")
async def websocket_project(ws: WebSocket, project_id: uuid.UUID):
    """Per-project WebSocket for indexing progress, file changes, etc."""
    channel = f"project:{project_id}"
    await ws_manager.connect(ws, channel)
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, channel)


# --- Static files ---

@app.get("/", include_in_schema=False)
async def serve_root():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- CLI entry point ---

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8420"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
