# -*- coding: utf-8 -*-
"""ReMe-backed memory manager for LitePaw agents.

Simplified from QwenPaw's ReMeLightMemoryManager — stripped inbox push,
proactive queries, auto-memory search, and session ID encoding.
"""

import asyncio
import logging
import os
from typing import Any

from agentscope.message import Msg, TextBlock
from agentscope.message import ToolResultState
from agentscope.tool import ToolChunk

from .base_memory_manager import BaseMemoryManager
from .prompts import build_memory_guidance_prompt
from .reme_config import get_reme_app_config

logger = logging.getLogger(__name__)

os.environ.setdefault("REME_DISABLE_LOGURU", "true")

NO_MEMORY_RESULTS = "(no memory results)"


def _tool_chunk(text: str, *, ok: bool = True) -> ToolChunk:
    return ToolChunk(
        is_last=True,
        state=ToolResultState.SUCCESS if ok else ToolResultState.ERROR,
        content=[TextBlock(type="text", text=text)],
    )


class ReMeLightMemoryManager(BaseMemoryManager):
    """Memory manager backed by ReMe.

    ReMe uses the LitePaw workspace root as its vault. Daily memory,
    digest memory, search, and auto-memory are executed through ReMe jobs.
    """

    def __init__(
        self,
        working_dir: str,
        agent_id: str,
        *,
        language: str = "zh",
        timezone: str = "Asia/Shanghai",
        metadata_dir: str = "mem_metadata",
        session_dir: str = "mem_session",
        mem_session_dir: str = "mem_agent",
        resource_dir: str = "resource",
        daily_dir: str = "memory",
        digest_dir: str = "digest",
        embedding_backend: str = "",
        embedding_model: str = "",
        embedding_api_key: str = "",
        embedding_base_url: str = "",
        embedding_dimensions: int = 1024,
        llm_model: str | None = None,
        llm_api_key: str | None = None,
        llm_base_url: str | None = None,
    ):
        super().__init__(working_dir=working_dir, agent_id=agent_id)
        self._language = language
        self._daily_dir = daily_dir
        self._reme = None
        self._reindex_lock = asyncio.Lock()

        # LLM config for summarization
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key
        self._llm_base_url = llm_base_url

        self._reme_config = get_reme_app_config(
            working_dir=working_dir,
            language=language,
            timezone=timezone,
            metadata_dir=metadata_dir,
            session_dir=session_dir,
            mem_session_dir=mem_session_dir,
            resource_dir=resource_dir,
            daily_dir=daily_dir,
            digest_dir=digest_dir,
            embedding_backend=embedding_backend,
            embedding_model=embedding_model,
            embedding_api_key=embedding_api_key,
            embedding_base_url=embedding_base_url,
            embedding_dimensions=embedding_dimensions,
        )

        try:
            from reme import ReMe

            self._reme = ReMe(**self._reme_config)
        except ImportError:
            logger.warning("ReMe import failed; memory disabled")
            self._reme = None

    async def start(self) -> None:
        """Start the embedded ReMe application."""
        if self._reme is None:
            return
        await self._update_reme_model()
        try:
            await self._reme.start()
            logger.info("ReMe memory manager started for agent '%s'", self.agent_id)
        except Exception:
            logger.exception("ReMe start failed")

    async def close(self) -> bool:
        """Close ReMe and cleanup background worker state."""
        worker_stopped = await self._shutdown_summarize_worker()
        if self._reme is not None:
            try:
                await self._reme.close()
            except Exception:
                logger.exception("ReMe close failed")
                return False
        self._reme = None
        return worker_stopped

    def get_memory_prompt(self) -> str:
        """Return memory guidance for system prompt injection."""
        return build_memory_guidance_prompt(self._language, daily_dir=self._daily_dir)

    def list_memory_tools(self):
        """Return memory tool functions to register with the agent toolkit."""
        return [self.memory_search]

    async def _update_reme_model(self) -> None:
        """Inject LitePaw's LLM into ReMe's default LLM component."""
        if self._reme is None or self._llm_model is None:
            return
        try:
            from agentscope.model import DashScopeChatModel, OpenAIChatModel
            from agentscope.formatter import DashScopeFormatter, OpenAIChatFormatter

            if self._llm_base_url:
                model = OpenAIChatModel(
                    model_name=self._llm_model,
                    api_key=self._llm_api_key or "",
                    base_url=self._llm_base_url,
                    stream=True,
                )
                formatter = OpenAIChatFormatter()
            else:
                model = DashScopeChatModel(
                    model_name=self._llm_model,
                    api_key=self._llm_api_key or "",
                    stream=True,
                )
                formatter = DashScopeFormatter()

            await self._reme.update_component("as_llm", "default", model=model)
            # Store formatter for later use if needed
            self._formatter = formatter
        except Exception:
            logger.exception("Failed to update ReMe LLM component")

    async def _run_reme_job(
        self,
        name: str,
        *,
        needs_llm: bool = False,
        **kwargs: Any,
    ) -> Any | None:
        if self._reme is None or not getattr(self._reme, "is_started", False):
            logger.debug("ReMe job skipped; app not started: %s", name)
            return None
        try:
            if needs_llm:
                await self._update_reme_model()
            response = await self._reme.run_job(name, **kwargs)
            return response
        except Exception:
            logger.exception("ReMe job failed: %s", name)
            return None

    async def memory_search(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0,
    ) -> str:
        """Search memory files semantically."""
        query = query.strip()
        if not query:
            return "Error: query cannot be empty"

        response = await self._run_reme_job(
            "search",
            query=query,
            limit=max(1, max_results),
            min_score=max(0.0, min_score),
        )
        if response is None:
            return "ReMe is not started."
        return str(response.answer or "").strip() or NO_MEMORY_RESULTS

    async def summarize(self, messages: list[Msg], **kwargs) -> str:
        """Persist conversation messages through ReMe auto-memory."""
        if not messages:
            return ""
        session_id = str(kwargs.get("session_id") or "")
        if not session_id:
            logger.warning("ReMe summarize skipped; session_id is empty")
            return ""

        response = await self._run_reme_job(
            "auto_memory",
            needs_llm=True,
            messages=[msg.model_dump(mode="json") for msg in messages],
            session_id=session_id,
            memory_hint=str(kwargs.get("memory_hint") or ""),
        )
        if response is None:
            return ""
        return str(response.answer or "")

    async def dream(self, **kwargs) -> None:
        """Run one ReMe auto-dream pass."""
        response = await self._run_reme_job(
            "auto_dream",
            needs_llm=True,
            date=str(kwargs.get("date") or ""),
            hint=str(kwargs.get("hint") or ""),
        )
        if response is not None and not response.success:
            raise RuntimeError(str(response.answer))

    async def rebuild_index(self) -> Any | None:
        """Clear and rebuild the ReMe search index on explicit request."""
        if self._reindex_lock.locked():
            raise RuntimeError("Memory index rebuild is already running")
        async with self._reindex_lock:
            return await self._run_reme_job("reindex")
