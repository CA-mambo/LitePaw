# -*- coding: utf-8 -*-
"""Tests for LitePaw server/ws_server module (REST API integration tests)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from litepaw.config.settings import Settings
from litepaw.server.ws_server import create_app


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with memory files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        # Create sample memory files
        (workspace / "MEMORY.md").write_text("# My Memory\n- User likes Python", encoding="utf-8")
        (memory_dir / "2026-08-01.md").write_text("# Day 1\nTalked about AI", encoding="utf-8")
        (memory_dir / "2026-08-02.md").write_text("# Day 2\nDiscussed deployment", encoding="utf-8")

        yield workspace


@pytest.fixture
def settings_with_workspace(temp_workspace):
    """Settings pointing to temporary workspace with mocked agent."""
    return Settings(
        agent_id="test-agent",
        workspace_dir=str(temp_workspace),
        llm={"model": "qwen-plus", "api_key": "test-key"},
    )


class TestMemoryRESTAPI:
    """Tests for memory REST endpoints."""

    @pytest.fixture
    def client_with_agent(self, settings_with_workspace, temp_workspace):
        """Create test client with mocked agent."""
        from litepaw.server import ws_server

        # Mock agent and memory
        mock_memory = MagicMock()
        mock_memory.memory_search = MagicMock(return_value="MEMORY.md: User likes Python")
        mock_memory.rebuild_index = MagicMock()

        mock_agent = MagicMock()
        mock_agent._memory = mock_memory

        # Patch create_app's closure variables
        app = create_app(settings_with_workspace)

        # Manually inject mock agent into the app's closure
        # This requires accessing the closure through the route functions
        for route in app.routes:
            if hasattr(route, 'endpoint'):
                # Find the websocket_chat and memory endpoint functions
                pass

        # Alternative: use lifespan to initialize agent, then patch
        # For now, test endpoints that don't require agent

        return TestClient(app), temp_workspace

    def test_W5_export_memory_empty_client(self, settings_with_workspace):
        """W5: Export works without agent by reading files directly."""
        app = create_app(settings_with_workspace)
        client = TestClient(app)
        response = client.post("/api/memory/export")
        # Without agent, export still works (reads files directly)
        assert response.status_code == 200
        data = response.json()
        assert "memory_files" in data

    def test_W8_list_memory_empty_workspace(self):
        """W8: List memory on empty workspace returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(workspace_dir=tmpdir)
            app = create_app(settings)
            client = TestClient(app)
            response = client.post("/api/memory/list")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert data["files"] == []

    def test_W9_list_memory_with_files(self, settings_with_workspace):
        """W9: List memory returns files."""
        app = create_app(settings_with_workspace)
        client = TestClient(app)
        response = client.post("/api/memory/list")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        paths = [f["path"] for f in data["files"]]
        assert "MEMORY.md" in paths
        assert "memory/2026-08-02.md" in paths
        assert "memory/2026-08-01.md" in paths

    def test_W6_export_memory_with_files(self, settings_with_workspace):
        """W6: Export returns memory_files dict."""
        app = create_app(settings_with_workspace)
        client = TestClient(app)
        response = client.post("/api/memory/export")
        assert response.status_code == 200
        data = response.json()
        assert "memory_files" in data
        assert "MEMORY.md" in data["memory_files"]
        assert "memory/2026-08-01.md" in data["memory_files"]

    def test_W7_import_memory(self, settings_with_workspace):
        """W7: Import writes files to workspace."""
        app = create_app(settings_with_workspace)
        client = TestClient(app)
        response = client.post("/api/memory/import", json={
            "memory_files": {
                "MEMORY.md": "# Imported Memory\n- New content",
                "memory/2026-08-03.md": "# Day 3\nImported data",
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert "MEMORY.md" in data["imported"]

        # Verify files were written
        workspace = Path(settings_with_workspace.workspace_dir)
        assert (workspace / "MEMORY.md").read_text(encoding="utf-8") == "# Imported Memory\n- New content"

    def test_W10_search_memory_503_without_agent(self):
        """W10 variant: search returns 503 without agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(workspace_dir=tmpdir)
            app = create_app(settings)
            client = TestClient(app)
            response = client.post("/api/memory/search", json={"query": "test"})
            assert response.status_code == 503


class TestWSServer:
    """Tests for WebSocket server creation."""

    def test_W1_create_app_returns_fastapi(self):
        """W1: create_app returns FastAPI instance."""
        settings = Settings()
        app = create_app(settings)
        assert app is not None
        assert app.title == "LitePaw"

    def test_W3_W4_websocket_empty_message(self):
        """W3 + W4: WebSocket skips empty messages and handles plain text."""
        # This requires actual WS connection testing which needs running server
        # Marked as placeholder for now
        pytest.skip("Requires full WS connection test with mock agent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
