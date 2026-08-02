# -*- coding: utf-8 -*-
"""Embedded ReMe application configuration for LitePaw memory.

Simplified from QwenPaw's reme_config.py — removed AgentProfileConfig
dependency, uses flat dict parameters instead.
"""

from copy import deepcopy
from typing import Any

_MAX_FILE_BYTES = 10 * 1024 * 1024

_OPENAI_COMPAT_EMBEDDING_BACKENDS = {
    "openai",
    "dashscope",
    "dashscope_multimodal",
}


def build_reme_app_config(
    *,
    working_dir: str,
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
) -> dict[str, Any]:
    """Build ReMe Application kwargs for embedded LitePaw usage."""
    cfg = _base_config()
    _apply_embedding_config(
        cfg,
        backend=embedding_backend,
        model=embedding_model,
        api_key=embedding_api_key,
        base_url=embedding_base_url,
        dimensions=embedding_dimensions,
    )
    cfg.update(
        {
            "workspace_dir": working_dir,
            "metadata_dir": metadata_dir,
            "session_dir": session_dir,
            "mem_session_dir": mem_session_dir,
            "resource_dir": resource_dir,
            "daily_dir": daily_dir,
            "digest_dir": digest_dir,
            "language": language,
            "timezone": timezone,
            "enable_logo": False,
            "log_to_console": True,
        },
    )
    return cfg


def _base_config() -> dict[str, Any]:
    """Return the ReMe config shape used by LitePaw."""
    watch_dirs = ["daily_dir", "digest_dir"]
    watch_suffixes = ["md"]

    return {
        "service": {"backend": "http"},
        "jobs": {
            "index_update_loop": {
                "backend": "background",
                "max_file_bytes": _MAX_FILE_BYTES,
                "watch_dirs": watch_dirs,
                "watch_suffixes": watch_suffixes,
                "steps": [
                    {
                        "backend": "init_changes_step",
                        "monitor_type": "file_store",
                        "monitor_name": "default",
                        "dispatch_steps": ["update_index_step"],
                    },
                    {
                        "backend": "watch_changes_step",
                        "dispatch_steps": [
                            {"backend": "update_index_step", "persist": False},
                        ],
                    },
                ],
            },
            "search": {
                "backend": "base",
                "description": "Hybrid workspace search (vector + BM25, RRF-fused).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "search query"},
                        "limit": {"type": "integer", "description": "max results", "default": 5},
                        "min_score": {"type": "number", "description": "min fused score", "default": 0.0},
                    },
                    "required": ["query"],
                },
                "steps": [
                    {
                        "backend": "search_step",
                        "vector_weight": 0.7,
                        "candidate_multiplier": 3.0,
                        "expand_links": True,
                        "max_links_per_direction": 10,
                    },
                ],
            },
            "daily_write": {
                "backend": "base",
                "description": "Write a daily markdown note with conversation source frontmatter.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "session_id": {"type": "string"},
                        "content": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                    "required": ["name", "description", "session_id", "content"],
                },
                "steps": [{"backend": "daily_write_step"}],
            },
            "read": {
                "backend": "base",
                "description": "Read a markdown file under the vault.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start_line": {"type": "integer"},
                        "end_line": {"type": "integer"},
                    },
                    "required": ["path"],
                },
                "steps": [
                    {
                        "backend": "read_step",
                        "with_neighbors": False,
                        "max_neighbors_per_direction": 10,
                    },
                ],
            },
            "write": {
                "backend": "base",
                "description": "Write a markdown file with name/description frontmatter.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "content": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                    "required": ["path", "name", "description", "content"],
                },
                "steps": [{"backend": "write_step"}],
            },
            "edit": {
                "backend": "base",
                "description": "Find-and-replace in a markdown file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old": {"type": "string"},
                        "new": {"type": "string", "default": ""},
                    },
                    "required": ["path", "old", "new"],
                },
                "steps": [{"backend": "edit_step"}],
            },
            "auto_memory": {
                "backend": "base",
                "description": "Auto-memory: record conversation facts into a daily note.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "messages": {"type": "array", "items": {"type": "object"}},
                        "session_id": {"type": "string", "default": ""},
                        "memory_hint": {"type": "string"},
                    },
                    "required": ["messages"],
                },
                "steps": [{"backend": "auto_memory_step"}],
            },
            "auto_dream": {
                "backend": "base",
                "description": "Auto-dream: consolidate daily notes into digest memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "default": ""},
                        "hint": {"type": "string", "default": ""},
                    },
                },
                "steps": [
                    {"backend": "dream_extract_step"},
                    {"backend": "dream_integrate_step"},
                    {"backend": "dream_finish_step"},
                ],
            },
            "reindex": {
                "backend": "base",
                "description": "Wipe the file store and rebuild search index.",
                "parameters": {"type": "object", "properties": {}},
                "steps": [
                    {"backend": "clear_store_step"},
                    {
                        "backend": "init_changes_step",
                        "monitor_type": "file_store",
                        "monitor_name": "default",
                        "dispatch_steps": ["update_index_step"],
                    },
                ],
            },
        },
        "components": _base_components(),
    }


def _base_components() -> dict[str, Any]:
    return {
        "tokenizer": {"default": {"backend": "regex"}},
        "as_llm": {
            "default": {
                "backend": "openai",
                "model": "litepaw-injected",
                "stream": True,
                "context_size": 200000,
                "max_retries": 3,
                "credential": {"api_key": "", "base_url": ""},
                "parameters": {"max_tokens": 65536, "thinking_enable": False},
            },
        },
        "agent_wrapper": {
            "default": {
                "backend": "agentscope",
                "as_llm": "default",
                "permission_mode": "bypass",
                "react_config": {"max_iters": 30},
            },
        },
        "file_graph": {"default": {"backend": "local"}},
        "file_catalog": {
            "default": {"backend": "local"},
            "digest": {"backend": "local"},
        },
        "file_chunker": {
            "markdown": {
                "backend": "markdown",
                "supported_extensions": ["md"],
            },
        },
        "keyword_index": {
            "default": {"backend": "bm25", "tokenizer": "default"},
        },
        "as_embedding": {
            "default": {
                "backend": "openai",
                "model": "",
                "dimensions": 1024,
                "credential": {"api_key": "", "base_url": ""},
                "parameters": {},
            },
        },
        "embedding_store": {
            "default": {
                "backend": "local",
                "as_embedding": "default",
                "enable_cache": True,
                "max_cache_size": 3000,
                "max_input_length": 8192,
                "max_batch_size": 10,
            },
        },
        "file_store": {
            "default": {
                "backend": "local",
                "store_name": "local",
                "embedding_store": "default",
                "keyword_index": "default",
                "file_graph": "default",
            },
        },
    }


def _apply_embedding_config(
    cfg: dict[str, Any],
    *,
    backend: str,
    model: str,
    api_key: str,
    base_url: str,
    dimensions: int,
) -> None:
    """Apply embedding configuration into ReMe component config."""
    components = cfg["components"]
    if not backend or not model.strip():
        components["file_store"]["default"]["embedding_store"] = ""
        components.pop("embedding_store", None)
        components.pop("as_embedding", None)
        return

    components["as_embedding"]["default"].update(
        {
            "backend": backend,
            "model": model,
            "dimensions": dimensions,
            "credential": _embedding_credential(backend, api_key, base_url),
        },
    )
    if backend == "openai":
        components["as_embedding"]["default"]["pass_dimensions"] = True
    components["file_store"]["default"]["embedding_store"] = "default"


def _embedding_credential(backend: str, api_key: str, base_url: str) -> dict:
    """Build credential payload for embedding backend."""
    if backend in _OPENAI_COMPAT_EMBEDDING_BACKENDS:
        cred = {"api_key": api_key}
        if base_url.strip():
            cred["base_url"] = base_url.strip()
        return cred
    if backend == "ollama":
        return {"host": base_url.strip()} if base_url.strip() else {}
    return {}


def get_reme_app_config(**kwargs) -> dict[str, Any]:
    """Public wrapper returning a deep copy safe for caller mutation."""
    return deepcopy(build_reme_app_config(**kwargs))
