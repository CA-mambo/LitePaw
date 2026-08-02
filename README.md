# LitePaw

轻量级 AI 记忆对话服务，支持 WebSocket 流式对话与双向记忆检索，适用于个人博客集成。

## 特性

- WebSocket 流式对话 + 自动记忆检索
- ReMeLight 记忆引擎（BM25 关键词 / 可选向量语义搜索）
- 对话后自动提取并持久化记忆
- 可插拔 LLM 后端（DashScope / OpenAI 兼容）
- Docker 一键部署

## 快速开始

### 安装

```bash
uv sync
```

### 配置

最少只需设置一个环境变量：

```bash
export LITEPAW_LLM_API_KEY="your-api-key"
```

完整配置可通过 `.env` 或 `config.yaml`（复制 `.env.example` / `config.example.yaml`）：

```yaml
llm:
  model: "qwen-plus"
  api_key: "your-api-key"

memory:
  language: "zh"
  # 可选：向量语义搜索
  # embedding_backend: "dashscope"
  # embedding_model: "text-embedding-v3"
  # embedding_api_key: "your-embedding-key"
```

### 启动

```bash
uv run litepaw
```

服务默认监听 `0.0.0.0:8765`。

## 接口

### WebSocket 对话

连接 `ws://host:8765/ws/chat`，发送：

```json
{"content": "你还记得我上次说的项目吗？"}
```

流式返回：

```json
{"type": "chunk", "content": "是的", "done": false, "memory_used": true, "memory_files": ["MEMORY.md"]}
{"type": "done", "session_id": "abc12345"}
```

### REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/memory/export` | POST | 导出记忆（ZIP） |
| `/api/memory/import` | POST | 导入记忆 |
| `/api/memory/list-memory` | POST | 列出记忆文件 |
| `/api/memory/search` | POST | 搜索记忆 |

### CLI 工具

```bash
uv run litepaw-memory --workspace ./workspace export backup.zip
uv run litepaw-memory --workspace ./workspace import-memory backup.zip
uv run litepaw-memory --workspace ./workspace search-memory "关键词"
```

## 部署

### Docker

```bash
docker compose up -d
```

### Nginx 反代

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8765/ws/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
location /api/ {
    proxy_pass http://127.0.0.1:8765/api/;
}
```

### 前端接入

```js
const ws = new WebSocket('wss://your-domain/ws/chat');
ws.onopen = () => ws.send(JSON.stringify({ content: '你好！' }));
ws.onmessage = (e) => {
  const d = JSON.parse(e.data);
  if (d.type === 'chunk') appendToChat(d.content);
};
```

## 测试

```bash
uv run pytest tests/ -v
```

## 项目结构

```
src/litepaw/
├── config/     # Pydantic 配置模型
├── memory/     # ReMeLight 记忆引擎
├── agent/      # LLM + Memory 对话接口
├── server/     # FastAPI + WebSocket + REST
└── memory_tool.py  # CLI 工具
```

## License

MIT
