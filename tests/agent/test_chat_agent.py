# -*- coding: utf-8 -*-
"""Tests for LitePaw agent/chat_agent module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from litepaw.config.settings import Settings
from litepaw.agent.chat_agent import ChatAgent


@pytest.fixture
def mock_settings():
    """Create settings with dummy LLM config."""
    return Settings(
        agent_id="test-agent",
        workspace_dir="./test-workspace",
        llm={"model": "qwen-plus", "api_key": "test-key"},
    )


@pytest.fixture
def chat_agent(mock_settings):
    """Create ChatAgent instance."""
    return ChatAgent(mock_settings)


class TestChatAgentInit:
    """Tests for ChatAgent initialization."""

    def test_init_attributes(self, chat_agent):
        """Agent initializes with expected attributes."""
        assert chat_agent._history == []
        assert chat_agent._model is None
        assert chat_agent._memory is None
        assert chat_agent._initialized is False


class TestChatAgentAsync:
    """Tests for async ChatAgent behavior (mocked LLM)."""

    @pytest.fixture
    def patched_agent(self, mock_settings):
        """Create agent with mocked LLM and memory."""
        agent = ChatAgent(mock_settings)

        # Mock LLM
        mock_model = AsyncMock()

        # Create a proper async generator for streaming response
        async def mock_stream():
            yield MagicMock(text="你好")
            yield MagicMock(text="，")
            yield MagicMock(text="我是AI助手。")

        mock_model.return_value = mock_stream()
        agent._model = mock_model

        # Mock memory
        mock_memory = MagicMock()
        mock_memory.memory_search = AsyncMock(return_value="(no memory results)")
        mock_memory.get_memory_prompt.return_value = "## Memory guidance"
        mock_memory.start = AsyncMock()
        mock_memory.close = AsyncMock(return_value=True)
        mock_memory.add_summarize_task = MagicMock()
        agent._memory = mock_memory
        agent._initialized = True

        return agent

    @pytest.mark.asyncio
    async def test_chat_yields_chunks(self, patched_agent):
        """A3: Chat streams response with chunks."""
        chunks = []
        async for text, meta in patched_agent.chat("你好"):
            chunks.append((text, meta))

        assert len(chunks) == 3
        assert chunks[0][0] == "你好"
        assert chunks[0][1]["done"] is False
        assert chunks[-1][1]["done"] is False  # Stream chunks, done comes separately

    @pytest.mark.asyncio
    async def test_chat_memorySearchCalled(self, patched_agent):
        """A4: memory_search is called during chat."""
        async for _ in patched_agent.chat("你还记得吗"):
            pass

        patched_agent._memory.memory_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_historyAccumulates(self, patched_agent):
        """A5: History accumulates messages."""
        async for _ in patched_agent.chat("消息1"):
            pass
        async for _ in patched_agent.chat("消息2"):
            pass

        # Each chat adds 2 messages (user + assistant)
        assert len(patched_agent._history) == 4

    @pytest.mark.asyncio
    async def test_chat_historyTruncates(self, patched_agent):
        """A6: History truncates at 20 messages."""
        for i in range(12):
            async for _ in patched_agent.chat(f"消息{i}"):
                pass

        assert len(patched_agent._history) <= 20

    @pytest.mark.asyncio
    async def test_chat_errorReturnsErrorMessage(self, mock_settings):
        """A7: LLM exception returns error message."""
        agent = ChatAgent(mock_settings)

        # Mock LLM to raise
        mock_model = AsyncMock()
        mock_model.side_effect = RuntimeError("LLM failed")
        agent._model = mock_model

        mock_memory = MagicMock()
        mock_memory.memory_search = AsyncMock(return_value="(no memory results)")
        mock_memory.get_memory_prompt.return_value = "## Memory guidance"
        agent._memory = mock_memory
        agent._initialized = True

        chunks = []
        async for text, meta in agent.chat("test"):
            chunks.append((text, meta))

        assert len(chunks) == 1
        assert "错误" in chunks[0][0] or "error" in chunks[0][0].lower()
        assert chunks[0][1].get("error") is True

    @pytest.mark.asyncio
    async def test_close_cleanup(self, patched_agent):
        """A8: close() cleans up memory."""
        await patched_agent.close()
        assert patched_agent._memory is None
        assert patched_agent._initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
