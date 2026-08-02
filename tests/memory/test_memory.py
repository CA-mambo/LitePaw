# -*- coding: utf-8 -*-
"""Tests for LitePaw memory module."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from litepaw.memory.base_memory_manager import BaseMemoryManager
from litepaw.memory.prompts import build_memory_guidance_prompt
from litepaw.memory.reme_config import build_reme_app_config, get_reme_app_config


class TestMemoryPrompts:
    """Tests for memory guidance prompts."""

    def test_build_memory_guidance_prompt_zh(self):
        prompt = build_memory_guidance_prompt("zh", daily_dir="memory")
        assert "记忆" in prompt
        assert "MEMORY.md" in prompt
        assert "memory" in prompt

    def test_build_memory_guidance_prompt_en(self):
        prompt = build_memory_guidance_prompt("en", daily_dir="daily_notes")
        assert "Memory" in prompt
        assert "MEMORY.md" in prompt
        assert "daily_notes" in prompt

    def test_build_memory_guidance_prompt_default(self):
        prompt = build_memory_guidance_prompt("fr", daily_dir="memoires")
        assert "Memory" in prompt  # Falls back to English
        assert "memoires" in prompt


class TestRemeConfig:
    """Tests for ReMe configuration building."""

    def test_build_reme_app_config_basic(self):
        cfg = build_reme_app_config(
            working_dir="/tmp/workspace",
            language="zh",
            timezone="Asia/Shanghai",
            daily_dir="memory",
            digest_dir="digest",
        )
        assert cfg["workspace_dir"] == "/tmp/workspace"
        assert cfg["language"] == "zh"
        assert cfg["daily_dir"] == "memory"
        assert "jobs" in cfg
        assert "search" in cfg["jobs"]
        assert "components" in cfg

    def test_build_reme_app_config_embedding_disabled(self):
        cfg = build_reme_app_config(
            working_dir="/tmp/workspace",
            daily_dir="memory",
            digest_dir="digest",
            embedding_backend="",
            embedding_model="",
            embedding_api_key="",
            embedding_base_url="",
        )
        components = cfg["components"]
        assert components["file_store"]["default"]["embedding_store"] == ""
        assert "embedding_store" not in components
        assert "as_embedding" not in components

    def test_build_reme_app_config_embedding_enabled(self):
        cfg = build_reme_app_config(
            working_dir="/tmp/workspace",
            daily_dir="memory",
            digest_dir="digest",
            embedding_backend="openai",
            embedding_model="text-embedding-3-small",
            embedding_api_key="test-key",
            embedding_base_url="https://api.openai.com/v1",
            embedding_dimensions=1536,
        )
        components = cfg["components"]
        assert "embedding_store" in components
        assert "as_embedding" in components
        embed_cfg = components["as_embedding"]["default"]
        assert embed_cfg["backend"] == "openai"
        assert embed_cfg["credential"]["api_key"] == "test-key"

    def test_get_reme_app_config_returns_deep_copy(self):
        cfg1 = get_reme_app_config(
            working_dir="/tmp/ws",
            daily_dir="memory",
            digest_dir="digest",
        )
        cfg2 = get_reme_app_config(
            working_dir="/tmp/ws",
            daily_dir="memory",
            digest_dir="digest",
        )
        assert cfg1 is not cfg2


class TestMemoryFiles:
    """Tests for MEMORY.md and daily memory file handling."""

    def test_memory_md_read_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            memory_md = workspace / "MEMORY.md"
            content = "# My Memory\n\n- User likes Python\n- Prefers async code"
            memory_md.write_text(content, encoding="utf-8")
            assert memory_md.exists()
            assert memory_md.read_text(encoding="utf-8") == content

    def test_daily_memory_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            daily_dir = workspace / "memory"
            daily_dir.mkdir()
            (daily_dir / "2026-08-01.md").write_text("# Day 1\n\nTalked about AI", encoding="utf-8")
            (daily_dir / "2026-08-02.md").write_text("# Day 2\n\nDiscussed deployment", encoding="utf-8")

            md_files = sorted(daily_dir.glob("*.md"))
            assert len(md_files) == 2
            assert md_files[0].name == "2026-08-01.md"
            assert md_files[1].name == "2026-08-02.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
