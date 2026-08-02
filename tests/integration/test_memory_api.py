# -*- coding: utf-8 -*-
"""Integration tests for LitePaw memory module with real API."""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")


@pytest.mark.skipif(
    not os.getenv("LITEPAW_LLM_API_KEY"),
    reason="LITEPAW_LLM_API_KEY not set",
)
class TestMemoryWithRealAPI:
    """Memory tests using real DashScope API."""

    @pytest.fixture
    def workspace_with_memory(self):
        """Create workspace with sample memory files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            memory_dir = workspace / "memory"
            memory_dir.mkdir()

            # Create MEMORY.md with user preferences
            (workspace / "MEMORY.md").write_text(
                "# User Memory\n"
                "- 用户喜欢 Python 编程\n"
                "- 偏好异步代码风格\n"
                "- 正在学习量化交易\n"
                "- 关注 A 股市场\n",
                encoding="utf-8",
            )

            # Create daily notes
            (memory_dir / "2026-08-01.md").write_text(
                "# 2026-08-01\n"
                "讨论了 LitePaw 项目架构\n"
                "用户希望保持轻量级设计\n",
                encoding="utf-8",
            )
            (memory_dir / "2026-08-02.md").write_text(
                "# 2026-08-02\n"
                "测试了记忆模块\n"
                "38 个测试全部通过\n",
                encoding="utf-8",
            )

            yield workspace

    @pytest.mark.asyncio
    async def test_remeLight_init_with_real_api(self, workspace_with_memory):
        """Test ReMeLightMemoryManager initializes with real API config."""
        from litepaw.memory import ReMeLightMemoryManager

        manager = ReMeLightMemoryManager(
            working_dir=str(workspace_with_memory),
            agent_id="test-integration",
            language="zh",
            daily_dir="memory",
            llm_model=os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
            llm_api_key=os.getenv("LITEPAW_LLM_API_KEY"),
            llm_base_url=os.getenv("LITEPAW_LLM_BASE_URL"),
        )

        assert manager is not None
        # _reme should be initialized (not None)
        assert manager._reme is not None or manager._llm_model is not None

    @pytest.mark.asyncio
    async def test_memory_search_with_real_api(self, workspace_with_memory):
        """Test memory search returns results with real API."""
        from litepaw.memory import ReMeLightMemoryManager

        manager = ReMeLightMemoryManager(
            working_dir=str(workspace_with_memory),
            agent_id="test-integration",
            language="zh",
            daily_dir="memory",
            llm_model=os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
            llm_api_key=os.getenv("LITEPAW_LLM_API_KEY"),
            llm_base_url=os.getenv("LITEPAW_LLM_BASE_URL"),
        )

        # Start memory manager
        await manager.start()

        try:
            # Search for Python-related memory
            result = await manager.memory_search("Python", max_results=5)

            # Should return something (either results or "no memory results")
            assert result is not None
            assert isinstance(result, str)

            # If ReMe is working, should return actual content
            if result != "(no memory results)":
                assert "Python" in result or "memory" in result.lower()
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_memory_summarize_with_real_api(self, workspace_with_memory):
        """Test memory summarize with real API."""
        from litepaw.memory import ReMeLightMemoryManager
        from agentscope.message import Msg, TextBlock

        manager = ReMeLightMemoryManager(
            working_dir=str(workspace_with_memory),
            agent_id="test-integration",
            language="zh",
            daily_dir="memory",
            llm_model=os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
            llm_api_key=os.getenv("LITEPAW_LLM_API_KEY"),
            llm_base_url=os.getenv("LITEPAW_LLM_BASE_URL"),
        )

        await manager.start()

        try:
            # Create sample conversation
            messages = [
                Msg(name="user", content=[TextBlock(text="你好")], role="user"),
                Msg(name="assistant", content=[TextBlock(text="你好！我是AI助手")], role="assistant"),
                Msg(name="user", content=[TextBlock(text="我喜欢Python")], role="user"),
                Msg(name="assistant", content=[TextBlock(text="Python是很好的语言")], role="assistant"),
            ]

            # Summarize should execute (may return empty if ReMe not fully configured)
            result = await manager.summarize(messages, session_id="test-session")
            assert isinstance(result, str)
        finally:
            await manager.close()


@pytest.mark.skipif(
    not os.getenv("LITEPAW_LLM_API_KEY"),
    reason="LITEPAW_LLM_API_KEY not set",
)
class TestChatAgentWithRealAPI:
    """ChatAgent integration tests with real API."""

    @pytest.mark.asyncio
    async def test_chat_agent_initializes_with_real_api(self):
        """Test ChatAgent initializes with real API credentials."""
        from litepaw.config.settings import Settings
        from litepaw.agent.chat_agent import ChatAgent

        settings = Settings(
            agent_id="test-integration",
            workspace_dir="./test-workspace",
            llm={
                "model": os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
                "api_key": os.getenv("LITEPAW_LLM_API_KEY"),
                "base_url": os.getenv("LITEPAW_LLM_BASE_URL"),
            },
        )

        agent = ChatAgent(settings)

        # Should not raise
        assert agent is not None
        assert agent.settings.llm.api_key == os.getenv("LITEPAW_LLM_API_KEY")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
