# LitePaw — 轻量级 QwenPaw 记忆服务

从 QwenPaw 提取核心 ReMeLight 记忆模块，剥离前端、多 channel、MCP 工具市场等重型组件，仅保留 **LLM 对话 + 双向记忆读写** 能力，用于个人博客部署。

## 架构

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

## 功能

- ✅ WebSocket 流式对话接口
- ✅ 基于 ReMe 的语义记忆检索（MEMORY.md + daily memory）
- ✅ 对话后自动提取记忆
- ✅ 记忆导出/导入（支持 ZIP 归档）
- ✅ REST API 记忆管理
- ✅ 可插拔 LLM 后端（DashScope / OpenAI 兼容）

## 快速开始

### 1. 安装

```bash
uv sync
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入 api_key
```

最少配置：

```yaml
llm:
  model: "qwen-plus"
  api_key: "your-dashscope-api-key"

memory:
  language: "zh"
```

### 3. 启动服务

```bash
uv run litepaw --config config.yaml
# 或使用环境变量
export LITEPAW_LLM_MODEL=qwen-plus
export LITEPAW_LLM_API_KEY=your-key
uv run litepaw
```

服务默认监听 `0.0.0.0:8765`。

## 接口文档

### WebSocket 对话

连接 `ws://host:port/ws/chat`，发送 JSON：

```json
{"content": "你还记得我上次说的 xxx 吗？"}
```

服务端流式返回：

```json
{"type": "chunk", "content": "是的", "done": false, "memory_used": false, "memory_files": []}
{"type": "chunk", "content": "，我记得...", "done": false, "memory_used": true, "memory_files": ["MEMORY.md"]}
{"type": "done", "session_id": "abc12345"}
```

### REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/memory/export` | POST | 导出所有记忆文件 |
| `/api/memory/import` | POST | 导入记忆文件 |
| `/api/memory/list-memory` | POST | 列出所有记忆文件 |
| `/api/memory/search` | POST | 语义搜索记忆 |

### CLI 工具

```bash
uv run litepaw-memory --workspace ./workspace export memory-backup.zip
uv run litepaw-memory --workspace ./workspace import-memory memory-backup.zip
uv run litepaw-memory --workspace ./workspace list-memory
uv run litepaw-memory --workspace ./workspace search-memory "关键词"
```

## 项目结构

```
src/litepaw/
├── memory/                  # 记忆模块（移植自 QwenPaw）
│   ├── base_memory_manager.py    # 抽象基类
│   ├── reme_light_memory_manager.py  # ReMe 轻量记忆实现
│   ├── reme_config.py            # ReMe 配置构建
│   └── prompts.py                # 记忆引导提示词
├── agent/
│   └── chat_agent.py        # LLM + Memory 对话接口
├── config/
│   └── settings.py          # Pydantic 配置模型
├── server/
│   └── ws_server.py         # FastAPI + WebSocket + REST
└── memory_tool.py           # CLI 记忆管理工具
```

## 与 QwenPaw 的关系

**保留的核心：**
- `ReMeLightMemoryManager` — ReMe 轻量记忆引擎
- `build_reme_app_config` — ReMe 配置构建
- `build_memory_guidance_prompt` — 记忆引导提示词

**剥离的组件：**
- ❌ CLI / Tauri 桌面 / Web Console
- ❌ Telegram / Discord / WeChat Channel
- ❌ MCP 工具市场 / 插件系统
- ❌ Sandbox / Docker / Checkpoints / Governance

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

## 博客部署

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --no-dev
EXPOSE 8765
CMD ["uv", "run", "litepaw", "--config", "config.yaml"]
```

### Nginx 反向代理

```nginx
server {
    listen 443 ssl;
    server_name your-blog.example.com;

    location /ws/ {
        proxy_pass http://127.0.0.1:8765/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8765/api/;
        proxy_set_header Host $host;
    }
}
```

### 前端接入示例

```javascript
const ws = new WebSocket('wss://your-blog.example.com/ws/chat');
ws.onopen = () => ws.send(JSON.stringify({ content: '你好！' }));
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'chunk') appendToChat(data.content);
    else if (data.type === 'done') console.log('Done');
};
```

## 测试

```bash
uv run pytest tests/ -v
# 38 passed, 1 skipped (WebSocket 连接测试需运行中服务)
```

## 下一步（可选扩展）

- [ ] 添加 agent_md_manager.py（MEMORY.md 自动维护）
- [ ] 多会话隔离（每个访客独立记忆）
- [ ] 记忆过滤/去重中间件
- [ ] 更多 LLM 后端（Claude, Gemini 等）
- [ ] 性能优化：embedding 缓存、搜索索引预热

## License

MIT
