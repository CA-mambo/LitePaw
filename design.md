# LitePaw — QwenPaw 轻量记忆服务

## 目标

从 QwenPaw 中提取核心记忆模块（ReMeLight），剥离不需要的组件（前端、多 channel、MCP 工具市场、sandbox 等），构建一个轻量 WebSocket 记忆对话服务。

## 使用场景

- 部署到个人博客服务器
- 用户通过 WebSocket 与 agent 对话
- Agent 具备记忆能力：读记忆（MEMORY.md + daily memory）、写记忆（对话后自动提取）
- 记忆文件可导出，经中间服务过滤后合并到本地 QwenPaw 记忆

## 架构设计

```
┌──────────────────────────────────────┐
│         LitePaw Service              │
│                                      │
│  ┌────────────┐   ┌───────────────┐  │
│  │ WebSocket  │──▶│ Agent Core    │  │
│  │ Server     │   │ (LLM + Memory)│  │
│  └────────────┘   └───────┬───────┘  │
│                           │          │
│              ┌────────────▼───────┐  │
│              │ ReMeLight Memory   │  │
│              │ - memory_search    │  │
│              │ - summarize        │  │
│              │ - auto_memory      │  │
│              └────────┬───────────┘  │
│                       │              │
│              ┌────────▼───────┐      │
│              │ Memory Files   │      │
│              │ - MEMORY.md    │      │
│              │ - memory/*.md  │      │
│              └────────────────┘      │
└──────────────────────────────────────┘
```

## 需要保留的 QwenPaw 组件

### 核心依赖
| 模块 | 路径 | 用途 |
|------|------|------|
| Memory Manager | `src/qwenpaw/agents/memory/` | 记忆系统核心 |
| - base_memory_manager.py | | 抽象基类 |
| - reme_light_memory_manager.py | | ReMe 轻量记忆实现 |
| - reme_config.py | | ReMe 配置构建 |
| - prompts.py | | 记忆引导提示词 |
| - agent_md_manager.py | | MEMORY.md 管理 |
| Model Factory | `src/qwenpaw/agents/model_factory.py` | 创建 LLM 实例 |
| Config | `src/qwenpaw/config/config.py` (部分) | Agent 配置模型 |
| Agent Prompt | `src/qwenpaw/agents/prompt.py` (部分) | 系统提示词构建 |

### 可剥离的组件
- ❌ CLI (`src/qwenpaw/cli/`)
- ❌ Tauri Desktop (`src/qwenpaw/tauri/`)
- ❌ Web Console (`console/`)
- ❌ Channel 接入（Telegram, Discord, WeChat, Web 等）
- ❌ MCP Server 市场/工具插件系统
- ❌ Sandbox / Docker 隔离环境
- ❌ Checkpoints (`src/qwenpaw/checkpoints/`)
- ❌ Governance / Security / Tunnel
- ❌ Pawapp (`src/qwenpaw/pawapp/`)

## WebSocket 接口设计

### 连接
```
ws://host:port/ws/chat
```

### 消息格式

**客户端 → 服务端:**
```json
{
  "type": "message",
  "content": "你还记得我们上次聊的xxx吗？"
}
```

**服务端 → 客户端 (流式):**
```json
{
  "type": "chunk",
  "content": "是的，我记得...",
  "done": false
}
```

**服务端 → 客户端 (完成):**
```json
{
  "type": "chunk",
  "content": "...这是当时的结论。",
  "done": true,
  "memory_used": true,
  "memory_files": ["MEMORY.md", "memory/2026-08-01.md"]
}
```

### 记忆管理接口

```
POST /api/memory/export  → 导出当前记忆文件（zip）
POST /api/memory/import  → 导入外部记忆文件（zip）
POST /api/memory/list    → 列出所有记忆文件
POST /api/memory/search  → 语义搜索记忆
```

## 记忆文件结构

```
workspace/
├── MEMORY.md              # 长期记忆
├── memory/                # 每日记忆摘要
│   ├── 2026-08-01.md
│   └── 2026-08-02.md
├── mem_metadata/          # ReMe 元数据
└── mem_session/           # ReMe 会话日志
```

## 技术栈

- **Python**: 3.10+
- **包管理**: uv
- **WebSocket**: websockets / fastapi
- **LLM**: 通过 QwenPaw 的 model_factory 接入（支持 OpenAI/Dashscope 兼容）
- **记忆引擎**: ReMe (复用 QwenPaw 的 ReMeLightMemoryManager)

## 依赖精简策略

1. 复制 `src/qwenpaw/agents/memory/` 到 `litepaw/memory/`
2. 复制 `src/qwenpaw/config/` 中需要的配置模型
3. 修复导入路径（`qwenpaw.*` → `litepaw.*`）
4. 剥离不需要的依赖（cli, tauri, channels, mcp, sandbox, checkpoints）
5. 保留 `model_factory.py` 用于 LLM 创建
6. 重写 `__init__.py` 和入口点

## 初始版本目标

- [x] 分析 QwenPaw 记忆模块依赖
- [ ] 创建项目骨架（入口、配置、WebSocket server）
- [ ] 移植 ReMeLightMemoryManager
- [ ] 实现 WebSocket 对话接口
- [ ] 实现记忆导出/导入
- [ ] 测试验证
- [ ] 部署文档
