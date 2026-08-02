# -*- coding: utf-8 -*-
"""Abstract base class for LitePaw memory managers.

Simplified from QwenPaw's BaseMemoryManager — stripped of
context compaction, token estimation, middleware hooks, and
auto-memory turn state tracking.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from agentscope.message import Msg

logger = logging.getLogger(__name__)


class BaseMemoryManager(ABC):
    """Abstract base class for LitePaw memory manager backends.

    Lifecycle:
        1. Instantiate with ``working_dir`` and ``agent_id``.
        2. ``await start()`` – initialize storage backend.
        3. Use ``summarize()``, ``memory_search()`` during session.
        4. ``await close()`` – flush and release resources.
    """

    enabled = True

    def __init__(self, working_dir: str, agent_id: str):
        self.working_dir: str = working_dir
        self.agent_id: str = agent_id
        self._task_counter: int = 0
        self._task_queue: asyncio.Queue[
            tuple[str, list[Msg], dict]
        ] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._worker_stopping = False

    @abstractmethod
    async def start(self) -> None:
        """Initialize the storage backend. Called once after instantiation."""

    @abstractmethod
    async def close(self) -> bool:
        """Flush pending state and release resources."""

    @abstractmethod
    def get_memory_prompt(self) -> str:
        """Return the memory guidance prompt for system prompt injection."""

    @abstractmethod
    def list_memory_tools(self) -> list[Callable[..., Any]]:
        """Return tool functions exposed to the agent for memory access."""

    async def summarize(self, messages: list[Msg], **kwargs) -> str:
        """Summarize conversation messages and persist to memory.

        Override to implement actual summarization. Base returns empty.
        """
        return ""

    async def dream(self, **kwargs) -> None:
        """Optimize memory files via a background agent pass.

        Override to implement actual memory optimization. Base does nothing.
        """
        return None

    async def memory_search(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0,
    ) -> str:
        """Search memory for relevant content.

        Override to implement semantic or keyword search.
        """
        return ""

    def add_summarize_task(self, messages: list[Msg], **kwargs) -> None:
        """Schedule a background summarization task without blocking."""
        self._worker_stopping = False
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._summarize_worker())
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        self._task_queue.put_nowait((task_id, messages, kwargs))

    async def _summarize_worker(self) -> None:
        """Background worker that processes summarize tasks serially."""
        while not self._worker_stopping:
            task_id, messages, kwargs = await self._task_queue.get()
            if self._worker_stopping:
                return
            try:
                await self.summarize(messages=messages, **kwargs)
            except asyncio.CancelledError:
                raise
            except BaseException:
                logger.exception("Summarize task %s failed", task_id)

    async def _shutdown_summarize_worker(
        self,
        timeout: float = 5.0,
    ) -> bool:
        """Stop the summary worker without allowing shutdown to hang."""
        self._worker_stopping = True
        worker = self._worker_task
        if worker is None:
            return True

        if not worker.done():
            worker.cancel()
            done, _pending = await asyncio.wait({worker}, timeout=timeout)
            if not done:
                worker.cancel()
                logger.error(
                    "Summary worker did not stop within %.1fs: agent_id=%s",
                    timeout,
                    self.agent_id,
                )
                return False

        self._worker_task = None
        return True
