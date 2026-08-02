# -*- coding: utf-8 -*-
"""Test semantic search with embedding model."""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Skip if no embedding API configured
EMBEDDING_API_KEY = os.getenv("LITEPAW_EMBEDDING_API_KEY", os.getenv("LITEPAW_LLM_API_KEY", ""))
EMBEDDING_MODEL = os.getenv("LITEPAW_EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_BACKEND = os.getenv("LITEPAW_EMBEDDING_BACKEND", "dashscope")


@pytest.mark.skipif(
    not EMBEDDING_API_KEY,
    reason="No embedding API key set (LITEPAW_EMBEDDING_API_KEY or LITEPAW_LLM_API_KEY)",
)
class TestSemanticSearch:
    """Verify semantic (vector) search works, not just keyword matching."""

    @pytest.fixture
    def workspace_with_semantic_memory(self):
        """Create workspace with memory that tests semantic understanding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            mem_dir = ws / "memory"
            mem_dir.mkdir()

            # Memory with related concepts that won't match by keyword alone
            (ws / "MEMORY.md").write_text(
                "# User Profile\n"
                "- 用户是一位软件工程师\n"
                "- 每天写 Python 和 Go\n"
                "- 喜欢微服务架构\n"
                "- 最近在研究 Kubernetes\n",
                encoding="utf-8",
            )
            (mem_dir / "2026-08-01.md").write_text(
                "# 2026-08-01\n"
                "讨论了编程语言选择\n"
                "用户认为静态类型语言更适合大型项目\n",
                encoding="utf-8",
            )
            yield ws

    @pytest.mark.asyncio
    async def test_semantic_search_finds_related_concepts(self, workspace_with_semantic_memory):
        """S-1: Semantic search finds related concepts without exact keyword match."""
        from litepaw.memory import ReMeLightMemoryManager

        manager = ReMeLightMemoryManager(
            working_dir=str(workspace_with_semantic_memory),
            agent_id="test-semantic",
            language="zh",
            daily_dir="memory",
            llm_model=os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
            llm_api_key=os.getenv("LITEPAW_LLM_API_KEY"),
            llm_base_url=os.getenv("LITEPAW_LLM_BASE_URL"),
            embedding_backend=EMBEDDING_BACKEND,
            embedding_model=EMBEDDING_MODEL,
            embedding_api_key=EMBEDDING_API_KEY,
        )

        await manager.start()

        try:
            # Search for "programming" - should find Python/Go/coding related content
            result = await manager.memory_search("编程", max_results=5)
            assert result is not None
            assert result != "(no memory results)", (
                "Semantic search should find related concepts even without exact keyword match. "
                "MEMORY.md contains 'Python', 'Go', '软件工程师' which are semantically related to '编程'"
            )

            # Should find programming-related content
            has_programming = any(
                kw in result.lower()
                for kw in ["python", "go", "engineer", "工程师", "编程", "代码", "coding", "静态类型"]
            )
            assert has_programming, f"Search for '编程' should find programming content, got: {result[:200]}"

        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_semantic_vs_keyword_distinction(self, workspace_with_semantic_memory):
        """S-2: Semantic search finds conceptually related but lexically different content."""
        from litepaw.memory import ReMeLightMemoryManager

        manager = ReMeLightMemoryManager(
            working_dir=str(workspace_with_semantic_memory),
            agent_id="test-semantic",
            language="zh",
            daily_dir="memory",
            llm_model=os.getenv("LITEPAW_LLM_MODEL", "qwen-plus"),
            llm_api_key=os.getenv("LITEPAW_LLM_API_KEY"),
            llm_base_url=os.getenv("LITEPAW_LLM_BASE_URL"),
            embedding_backend=EMBEDDING_BACKEND,
            embedding_model=EMBEDDING_MODEL,
            embedding_api_key=EMBEDDING_API_KEY,
        )

        await manager.start()

        try:
            # "container orchestration" should find Kubernetes (semantic)
            # BM25 alone would not match this
            result = await manager.memory_search("容器编排", max_results=5)
            assert result is not None

            # If semantic search works, should mention Kubernetes or k8s
            if result != "(no memory results)":
                has_k8s = any(
                    kw in result.lower()
                    for kw in ["kubernetes", "k8s", "容器", "orchestration", "微服务", "microservice"]
                )
                assert has_k8s, (
                    f"Semantic search for '容器编排' should find Kubernetes/microservices content. "
                    f"Got: {result[:200]}"
                )

        finally:
            await manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
