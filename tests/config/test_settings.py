# -*- coding: utf-8 -*-
"""Tests for LitePaw config/settings module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from litepaw.config.settings import Settings, LLMConfig, MemoryConfig


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_default_values(self):
        """C5: LLMConfig default values."""
        cfg = LLMConfig()
        assert cfg.model == "qwen-plus"
        assert cfg.api_key == ""
        assert cfg.base_url is None
        assert cfg.max_tokens == 8192

    def test_custom_values(self):
        cfg = LLMConfig(model="gpt-4", api_key="test-key", base_url="https://api.example.com")
        assert cfg.model == "gpt-4"
        assert cfg.api_key == "test-key"
        assert cfg.base_url == "https://api.example.com"


class TestMemoryConfig:
    """Tests for MemoryConfig model."""

    def test_default_values(self):
        """C6: MemoryConfig default values."""
        cfg = MemoryConfig()
        assert cfg.backend == "remelight"
        assert cfg.language == "zh"
        assert cfg.daily_dir == "memory"
        assert cfg.metadata_dir == "mem_metadata"
        assert cfg.session_dir == "mem_session"
        assert cfg.digest_dir == "digest"
        assert cfg.embedding_backend == ""
        assert cfg.embedding_model == ""
        assert cfg.embedding_dimensions == 1024


class TestSettings:
    """Tests for Settings model."""

    def test_default_init(self):
        """C1: Settings default initialization."""
        s = Settings()
        assert s.agent_id == "litepaw-agent"
        assert s.workspace_dir == "./workspace"
        assert s.host == "0.0.0.0"
        assert s.port == 8765
        assert isinstance(s.llm, LLMConfig)
        assert isinstance(s.memory, MemoryConfig)

    def test_yaml_roundtrip(self):
        """C2 + C3: YAML load and save."""
        original = Settings(
            agent_id="test-agent",
            workspace_dir="/tmp/test-ws",
            port=9999,
            llm=LLMConfig(model="gpt-4", api_key="secret"),
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(original.model_dump(), f)
            path = f.name

        try:
            loaded = Settings.from_yaml(path)
            assert loaded.agent_id == "test-agent"
            assert loaded.workspace_dir == "/tmp/test-ws"
            assert loaded.port == 9999
            assert loaded.llm.model == "gpt-4"
            assert loaded.llm.api_key == "secret"
        finally:
            Path(path).unlink()

    def test_from_env(self):
        """C4: Settings from environment variables."""
        env_vars = {
            "LITEPAW_AGENT_ID": "env-agent",
            "LITEPAW_WORKSPACE": "/tmp/env-ws",
            "LITEPAW_LLM_MODEL": "claude-3",
            "LITEPAW_LLM_API_KEY": "env-key",
            "LITEPAW_LLM_BASE_URL": "https://env.api",
            "LITEPAW_LANGUAGE": "en",
            "LITEPAW_HOST": "127.0.0.1",
            "LITEPAW_PORT": "7777",
        }
        old_env = {}
        for k, v in env_vars.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v

        try:
            s = Settings.from_env()
            assert s.agent_id == "env-agent"
            assert s.workspace_dir == "/tmp/env-ws"
            assert s.llm.model == "claude-3"
            assert s.llm.api_key == "env-key"
            assert s.llm.base_url == "https://env.api"
            assert s.memory.language == "en"
            assert s.host == "127.0.0.1"
            assert s.port == 7777
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
