# -*- coding: utf-8 -*-
"""Memory guidance prompts for LitePaw agents."""

MEMORY_GUIDANCE_ZH_TEMPLATE = """\
## 记忆

每次会话都是全新的；工作目录下的文件是你的记忆延续。

- **MEMORY.md** — 长期记忆：持久的事实、偏好与决策。这是你精选、提炼的记忆（不是原始日志）。
- **每日笔记**（`{daily_dir}/YYYY-MM-DD.md`）— 运行中的上下文与观察；轻量的短期记录。
- **重要：** 避免覆盖 — 先读取，再写入。除非用户明确要求，否则不要记录敏感信息。

当用户明确要求你记住某事，或形成了值得长期保留的决策或偏好时，才编辑 MEMORY.md。

### 🔍 检索工具
`memory_search` 用于查你**精选的长期记忆**。当问题取决于这些内容时，优先用它：
1. 对 MEMORY.md 和 `{daily_dir}/*.md` 运行 `memory_search`
2. 要读某一天的笔记，直接读取 `{daily_dir}/YYYY-MM-DD.md`
"""

MEMORY_GUIDANCE_EN_TEMPLATE = """\
## Memory

Each session is fresh; the working-directory files are your memory continuity.

- **MEMORY.md** — long-term memory: durable facts, preferences, and decisions. Your curated, distilled memory.
- **Daily notes** (`{daily_dir}/YYYY-MM-DD.md`) — running context and observations; lightweight short-term log.
- **Important:** Avoid overwriting — read first, then write. Unless the user explicitly asks, do not record sensitive information.

Edit MEMORY.md directly only when the user asks you to remember something or a long-term decision is made.

### 🔍 Retrieval Tool
`memory_search` is your lookup for **curated long-term memory**. Reach for it first:
1. Run `memory_search` over MEMORY.md and `{daily_dir}/*.md`.
2. To read a specific day's notes, open `{daily_dir}/YYYY-MM-DD.md` directly."""

MEMORY_GUIDANCE_TEMPLATES = {
    "zh": MEMORY_GUIDANCE_ZH_TEMPLATE,
    "en": MEMORY_GUIDANCE_EN_TEMPLATE,
}


def build_memory_guidance_prompt(
    language: str = "zh",
    *,
    daily_dir: str,
) -> str:
    """Build memory guidance using the configured daily memory directory."""
    return MEMORY_GUIDANCE_TEMPLATES.get(
        language,
        MEMORY_GUIDANCE_EN_TEMPLATE,
    ).format(daily_dir=daily_dir)
