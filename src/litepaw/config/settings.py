# -*- coding: utf-8 -*-
"""LitePaw settings model."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM configuration for the agent."""

    model: str = Field(default="qwen-plus", description="LLM model name")
    api_key: str = Field(default="", description="LLM API key")
    base_url: Optional[str] = Field(default=None, description="LLM base URL")
    max_tokens: int = Field(default=8192, description="Max output tokens")


class MemoryConfig(BaseModel):
    """Memory subsystem configuration."""

    backend: str = Field(default="remelight", description="Memory backend")
    language: str = Field(default="zh", description="Language for memory prompts")
    daily_dir: str = Field(default="memory", description="Daily memory subdirectory")
    metadata_dir: str = Field(default="mem_metadata", description="ReMe metadata dir")
    session_dir: str = Field(default="mem_session", description="ReMe session dir")
    digest_dir: str = Field(default="digest", description="Digest memory dir")

    # Embedding config
    embedding_backend: str = Field(default="", description="Embedding backend (openai/dashscope/ollama)")
    embedding_model: str = Field(default="", description="Embedding model name")
    embedding_api_key: str = Field(default="", description="Embedding API key")
    embedding_base_url: str = Field(default="", description="Embedding base URL")
    embedding_dimensions: int = Field(default=1024, description="Embedding dimensions")


class Settings(BaseModel):
    """LitePaw top-level settings."""

    # Agent
    agent_id: str = Field(default="litepaw-agent", description="Agent identifier")
    workspace_dir: str = Field(default="./workspace", description="Memory workspace root")

    # LLM
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # Memory
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    # Server
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8765, description="Server bind port")

    @classmethod
    def from_yaml(cls, path: str) -> "Settings":
        """Load settings from a YAML file."""
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str) -> None:
        """Save settings to a YAML file."""
        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, allow_unicode=True)

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        import os
        return cls(
            agent_id=os.getenv("LITEPAW_AGENT_ID", "litepaw-agent"),
            workspace_dir=os.getenv("LITEPAW_WORKSPACE", "./workspace"),
            llm=LLMConfig(
                model=os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
                api_key=os.getenv("LITEPAW_LLM_API_KEY", ""),
                base_url=os.getenv("LITEPAW_LLM_BASE_URL") or None,
            ),
            memory=MemoryConfig(
                language=os.getenv("LITEPAW_LANGUAGE", "zh"),
                embedding_backend=os.getenv("LITEPAW_EMBEDDING_BACKEND", ""),
                embedding_model=os.getenv("LITEPAW_EMBEDDING_MODEL", ""),
                embedding_api_key=os.getenv("LITEPAW_EMBEDDING_API_KEY", ""),
                embedding_base_url=os.getenv("LITEPAW_EMBEDDING_BASE_URL", ""),
            ),
            host=os.getenv("LITEPAW_HOST", "0.0.0.0"),
            port=int(os.getenv("LITEPAW_PORT", "8765")),
        )
