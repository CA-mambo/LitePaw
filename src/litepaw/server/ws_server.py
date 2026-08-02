# -*- coding: utf-8 -*-
"""LitePaw WebSocket server implementation."""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..config.settings import Settings
from ..agent.chat_agent import ChatAgent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)


async def run_server(settings: Settings) -> None:
    """Run the LitePaw WebSocket server."""
    import uvicorn

    app = create_app(settings)
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def create_app(settings: Settings) -> FastAPI:
    """Create FastAPI application with LitePaw services."""

    # Ensure workspace directory exists
    workspace = Path(settings.workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    agent: ChatAgent | None = None
    manager = ConnectionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal agent
        agent = ChatAgent(settings)
        await agent.initialize()
        logger.info("LitePaw agent initialized")
        yield
        if agent:
            await agent.close()
            logger.info("LitePaw agent closed")

    app = FastAPI(
        title="LitePaw",
        description="Lightweight QwenPaw memory service",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket):
        """WebSocket endpoint for chat with memory."""
        await manager.connect(websocket)
        session_id = str(uuid.uuid4())[:8]

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                    content = message_data.get("content", "").strip()
                except json.JSONDecodeError:
                    content = data.strip()

                if not content:
                    continue

                if agent is None:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Agent not initialized",
                    })
                    continue

                # Stream response
                async for text_chunk, metadata in agent.chat(content, session_id=session_id):
                    await websocket.send_json({
                        "type": "chunk",
                        "content": text_chunk,
                        "done": metadata.get("done", False),
                        "memory_used": metadata.get("memory_used", False),
                        "memory_files": metadata.get("memory_files", []),
                    })

                # Send completion signal
                await websocket.send_json({
                    "type": "done",
                    "session_id": session_id,
                })

        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info("Client disconnected")
        except Exception:
            logger.exception("WebSocket error")
            manager.disconnect(websocket)

    @app.post("/api/memory/export")
    async def export_memory():
        """Export memory files as a JSON structure."""
        workspace = Path(settings.workspace_dir)
        memory_data: dict[str, str] = {}

        # Export MEMORY.md
        memory_md = workspace / "MEMORY.md"
        if memory_md.exists():
            memory_data["MEMORY.md"] = memory_md.read_text(encoding="utf-8")

        # Export daily memory files
        daily_dir = workspace / settings.memory.daily_dir
        if daily_dir.exists():
            for md_file in sorted(daily_dir.glob("*.md")):
                memory_data[f"{settings.memory.daily_dir}/{md_file.name}"] = md_file.read_text(encoding="utf-8")

        return {"memory_files": memory_data}

    @app.post("/api/memory/import")
    async def import_memory(data: dict[str, Any]):
        """Import memory files from a JSON structure."""
        workspace = Path(settings.workspace_dir)
        memory_files = data.get("memory_files", {})

        imported = []
        for rel_path, content in memory_files.items():
            target = workspace / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            imported.append(rel_path)

        # Rebuild search index if agent available
        if agent is not None and agent._memory is not None:
            try:
                await agent._memory.rebuild_index()
            except Exception:
                logger.exception("Failed to rebuild memory index after import")

        return {"imported": imported, "count": len(imported)}

    @app.post("/api/memory/list")
    async def list_memory():
        """List all memory files."""
        workspace = Path(settings.workspace_dir)
        files = []

        memory_md = workspace / "MEMORY.md"
        if memory_md.exists():
            files.append({
                "path": "MEMORY.md",
                "size": memory_md.stat().st_size,
            })

        daily_dir = workspace / settings.memory.daily_dir
        if daily_dir.exists():
            for md_file in sorted(daily_dir.glob("*.md"), reverse=True):
                files.append({
                    "path": f"{settings.memory.daily_dir}/{md_file.name}",
                    "size": md_file.stat().st_size,
                })

        return {"files": files, "count": len(files)}

    @app.post("/api/memory/search")
    async def search_memory(data: dict[str, Any]):
        """Search memory semantically."""
        if agent is None or agent._memory is None:
            return JSONResponse(status_code=503, content={"error": "Memory not initialized"})

        query = data.get("query", "").strip()
        if not query:
            return JSONResponse(status_code=400, content={"error": "Query is required"})

        max_results = data.get("max_results", 10)
        result = await agent._memory.memory_search(query, max_results=max_results)
        return {"query": query, "result": result}

    return app
