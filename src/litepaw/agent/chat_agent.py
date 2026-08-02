# -*- coding: utf-8 -*-
"""LitePaw ChatAgent — integrates LLM with memory system."""

import logging
from typing import AsyncGenerator

from agentscope.message import Msg, TextBlock
from agentscope.model import DashScopeChatModel, OpenAIChatModel
from agentscope.formatter import DashScopeChatFormatter, OpenAIChatFormatter

from ..config.settings import Settings
from ..memory import ReMeLightMemoryManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PREFIX = """\
你是一个有帮助的 AI 助手。你具备记忆能力，可以记住之前对话中用户分享的事实、偏好和决策。
每次对话都是全新的，但你可以通过记忆系统检索之前的信息来更好地回答用户问题。
当你不确定某事时，可以主动检索记忆或承认不知道。
"""


class ChatAgent:
    """Chat agent with integrated memory support.

    Wraps an LLM model and the ReMeLight memory manager into
    a simple streaming chat interface.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._history: list[Msg] = []
        self._model = None
        self._formatter = None
        self._memory: ReMeLightMemoryManager | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize model and memory manager."""
        if self._initialized:
            return

        # Initialize LLM
        llm_cfg = self.settings.llm
        if llm_cfg.base_url:
            from agentscope.credential import OpenAICredential
            self._model = OpenAIChatModel(
                model=llm_cfg.model,
                credential=OpenAICredential(api_key=llm_cfg.api_key, base_url=llm_cfg.base_url),
                stream=True,
            )
            self._formatter = OpenAIChatFormatter()
        else:
            from agentscope.credential import DashScopeCredential
            self._model = DashScopeChatModel(
                model=llm_cfg.model,
                credential=DashScopeCredential(api_key=llm_cfg.api_key),
                stream=True,
            )
            self._formatter = DashScopeChatFormatter()

        # Initialize memory
        mem_cfg = self.settings.memory
        self._memory = ReMeLightMemoryManager(
            working_dir=self.settings.workspace_dir,
            agent_id=self.settings.agent_id,
            language=mem_cfg.language,
            daily_dir=mem_cfg.daily_dir,
            metadata_dir=mem_cfg.metadata_dir,
            session_dir=mem_cfg.session_dir,
            digest_dir=mem_cfg.digest_dir,
            embedding_backend=mem_cfg.embedding_backend,
            embedding_model=mem_cfg.embedding_model,
            embedding_api_key=mem_cfg.embedding_api_key,
            embedding_base_url=mem_cfg.embedding_base_url,
            embedding_dimensions=mem_cfg.embedding_dimensions,
            llm_model=llm_cfg.model,
            llm_api_key=llm_cfg.api_key,
            llm_base_url=llm_cfg.base_url,
        )
        await self._memory.start()

        self._initialized = True
        logger.info("ChatAgent initialized successfully")

    async def close(self) -> None:
        """Cleanup resources."""
        if self._memory is not None:
            await self._memory.close()
            self._memory = None
        self._initialized = False

    def _build_system_prompt(self) -> str:
        """Build system prompt with memory guidance."""
        prompt = SYSTEM_PROMPT_PREFIX
        if self._memory:
            prompt += "\n\n" + self._memory.get_memory_prompt()
        return prompt

    async def chat(
        self,
        user_message: str,
        session_id: str = "default",
    ) -> AsyncGenerator[tuple[str, dict], None]:
        """Stream chat response with memory integration.

        Yields tuples of (text_chunk, metadata) where metadata may contain:
        - done: bool indicating stream completion
        - memory_used: bool indicating if memory was consulted
        - memory_files: list of memory files consulted

        Args:
            user_message: User's input text.
            session_id: Session identifier for memory tracking.
        """
        if not self._initialized:
            await self.initialize()

        # Step 1: Search memory for relevant context
        memory_used = False
        memory_files = []
        if self._memory:
            search_result = await self._memory.memory_search(user_message)
            if search_result and search_result != "(no memory results)":
                memory_used = True
                # Track which files were consulted (simplified)
                memory_files = ["MEMORY.md", f"{self.settings.memory.daily_dir}/"]

        # Step 2: Build messages
        system_msg = Msg(name="system", content=[TextBlock(text=self._build_system_prompt())], role="system")
        user_msg = Msg(name="user", content=[TextBlock(text=user_message)], role="user")
        messages = [system_msg] + self._history + [user_msg]

        # Step 3: Call LLM with streaming
        try:
            full_response = ""
            response = await self._model(messages)

            # Process streaming response
            if hasattr(response, '__aiter__'):
                async for chunk in response:
                    text = self._extract_text_from_chunk(chunk)
                    if text:
                        full_response += text
                        yield text, {"done": False, "memory_used": memory_used, "memory_files": memory_files}
            else:
                # Non-streaming response
                text = self._extract_text_from_chunk(response)
                if text:
                    full_response = text
                    yield text, {"done": True, "memory_used": memory_used, "memory_files": memory_files}

            # Step 4: Update history
            self._history.append(user_msg)
            assistant_msg = Msg(name="assistant", content=[TextBlock(text=full_response)], role="assistant")
            self._history.append(assistant_msg)

            # Step 5: Summarize to memory if enabled
            if self._memory and len(self._history) >= 4:
                self._memory.add_summarize_task(
                    messages=self._history[-4:],
                    session_id=session_id,
                )
                # Keep history bounded
                if len(self._history) > 20:
                    self._history = self._history[-16:]

        except Exception:
            logger.exception("Chat request failed")
            yield "抱歉，处理您的请求时出现了错误。", {"done": True, "error": True}

    @staticmethod
    def _extract_text_from_chunk(chunk) -> str:
        """Extract text content from an AgentScope model response chunk."""
        if hasattr(chunk, "text"):
            return chunk.text
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, TextBlock):
                        return block.text
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")
        return ""
