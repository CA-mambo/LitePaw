# LitePaw 测试计划

## 测试概览

本文档记录 LitePaw 各模块的预期行为、测试设计和测试执行计划。

---

## 模块测试设计

### 1. Config 模块 (`src/litepaw/config/settings.py`)

**预期行为：**
- `Settings` 应使用默认值正确初始化
- `from_yaml()` 应能加载 YAML 配置并覆盖默认值
- `to_yaml()` 应能序列化为 YAML 文件
- `from_env()` 应读取环境变量并构建配置
- `LLMConfig` 和 `MemoryConfig` 字段应有正确默认值

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| C1 | 默认初始化 | `Settings()` | agent_id="litepaw-agent", workspace_dir="./workspace", port=8765 |
| C2 | YAML 加载 | 有效 YAML 文件 | Settings 实例，字段匹配 YAML 内容 |
| C3 | YAML 序列化 | Settings 实例 | YAML 文件，可重新加载并内容一致 |
| C4 | 环境变量加载 | 设置 LITEPAW_* 环境变量 | Settings 实例匹配环境变量 |
| C5 | LLMConfig 默认值 | `LLMConfig()` | model="qwen-plus", api_key="", base_url=None |
| C6 | MemoryConfig 默认值 | `MemoryConfig()` | backend="remelight", language="zh", daily_dir="memory" |

---

### 2. Memory Prompts 模块 (`src/litepaw/memory/prompts.py`)

**预期行为：**
- `build_memory_guidance_prompt("zh", ...)` 返回中文提示词
- `build_memory_guidance_prompt("en", ...)` 返回英文提示词
- `build_memory_guidance_prompt("其他", ...)` 回退到英文
- daily_dir 参数应正确替换到模板中

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| P1 | 中文提示词 | language="zh", daily_dir="memory" | 包含"记忆"、"MEMORY.md"、"memory" |
| P2 | 英文提示词 | language="en", daily_dir="daily" | 包含"Memory"、"MEMORY.md"、"daily" |
| P3 | 回退行为 | language="fr", daily_dir="memo" | 包含"Memory"（英文回退）、"memo" |

---

### 3. ReMe Config 模块 (`src/litepaw/memory/reme_config.py`)

**预期行为：**
- `build_reme_app_config()` 返回包含 jobs、components 的字典
- embedding 为空时应从组件中移除 embedding 相关配置
- embedding 启用时应正确配置 backend、credential
- `get_reme_app_config()` 应返回深拷贝

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| R1 | 基础配置 | working_dir="/tmp", daily_dir="memory", digest_dir="digest" | 包含 workspace_dir, daily_dir, jobs, components |
| R2 | Embedding 禁用 | embedding_backend="" | components 中无 embedding_store, as_embedding |
| R3 | Embedding 启用 (OpenAI) | backend="openai", model="text-embedding", api_key="key" | embedding_store 存在, credential.api_key="key" |
| R4 | Embedding 启用 (DashScope) | backend="dashscope", model="text-embedding", api_key="key" | embedding_store 存在, credential.api_key="key" |
| R5 | 深拷贝验证 | 两次调用 get_reme_app_config() | 返回不同对象 (cfg1 is not cfg2) |

---

### 4. Memory Files 模块 (MEMORY.md + daily memory)

**预期行为：**
- MEMORY.md 可在 workspace 根读写
- daily memory 文件在 `{daily_dir}/YYYY-MM-DD.md` 格式下读写
- 文件编码应为 UTF-8

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| F1 | MEMORY.md 读写 | 写入内容 → 读取 | 内容一致 |
| F2 | daily 文件列出 | 创建 2 个 YYYY-MM-DD.md 文件 | glob 返回 2 个文件，按名称排序 |
| F3 | 中文编码 | 写入含中文内容 | 读取后内容无乱码 |

---

### 5. Base Memory Manager (`src/litepaw/memory/base_memory_manager.py`)

**预期行为：**
- `BaseMemoryManager` 为抽象类，不可直接实例化
- `add_summarize_task()` 将任务加入队列
- `_summarize_worker()` 串行处理队列中的任务
- `close()` 应停止 worker 并返回 bool

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| B1 | 抽象类不可实例化 | `BaseMemoryManager(...)` | TypeError |
| B2 | 任务队列 | 调用 add_summarize_task() | _task_queue 非空 |
| B3 | worker 处理任务 | 添加任务 → 等待 worker | 任务被调用 summarize() |

---

### 6. ReMeLight Memory Manager (`src/litepaw/memory/reme_light_memory_manager.py`)

**预期行为：**
- `start()` 初始化 ReMe 应用并调用 `_update_reme_model()`
- `close()` 关闭 ReMe 并停止 summarize worker
- `get_memory_prompt()` 返回格式化的记忆引导词
- `memory_search()` 调用 ReMe search job 并返回结果
- `summarize()` 调用 ReMe auto_memory job
- `dream()` 调用 ReMe auto_dream job
- ReMe 不可用时（import 失败）应优雅降级

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| M1 | 初始化 | working_dir, agent_id, llm_model | ReMeLightMemoryManager 实例 |
| M2 | start 成功 | _reme 存在 | _reme.start() 被调用 |
| M3 | close 清理 | _reme 存在 | _reme.close() 被调用, _reme=None, 返回 True |
| M4 | get_memory_prompt | language="zh", daily_dir="memory" | 包含"记忆"和"memory"的字符串 |
| M5 | memory_search 空查询 | query="" | "Error: query cannot be empty" |
| M6 | memory_search ReMe 未启动 | _reme=None | "ReMe is not started." |
| M7 | summarize 空消息 | messages=[] | "" |
| M8 | dream 成功 | date="2026-08-02" | response.success=True |
| M9 | ReMe import 失败 | ReMe 不可导入 | _reme=None, 不抛异常 |

---

### 7. Chat Agent (`src/litepaw/agent/chat_agent.py`)

**预期行为：**
- `initialize()` 创建 LLM 和 Memory 实例
- `chat()` 流式返回 (text_chunk, metadata) 元组
- memory_search 在每次对话前执行
- 历史消息在 `_history` 中累积
- 历史超过 20 条时截断保留最近 16 条
- LLM 异常时返回错误消息

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| A1 | 初始化 | Settings 实例 | _model 非 None, _memory 非 None, _initialized=True |
| A2 | 重复初始化 | 两次调用 initialize() | 仅执行一次（_initialized 守卫） |
| A3 | 对话流式输出 | chat("你好") | 至少 yield 一次 (text, {"done": False}) |
| A4 | 记忆检索 | chat("你还记得xxx吗") | memory_search 被调用，memory_used=True |
| A5 | 历史累积 | 4 次 chat() | _history 包含 4 条用户+助理消息 |
| A6 | 历史截断 | 22 次 chat() | _history 长度 <= 20 |
| A7 | LLM 异常 | _model 抛异常 | yield "抱歉，处理您的请求时出现了错误。", {"done": True, "error": True} |
| A8 | close 清理 | 调用 close() | _memory.close() 被调用, _initialized=False |

---

### 8. WebSocket Server (`src/litepaw/server/ws_server.py`)

**预期行为：**
- `create_app()` 返回 FastAPI 实例
- `/ws/chat` WebSocket 端点接受消息并流式返回
- `/api/memory/export` 返回 memory_files 字典
- `/api/memory/import` 写入文件并返回 imported 列表
- `/api/memory/list` 返回文件列表和大小
- `/api/memory/search` 调用 memory_search
- Agent 未初始化时返回 503

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| W1 | create_app | Settings 实例 | FastAPI 实例 |
| W2 | WebSocket 连接 | ws.connect() → send({"content":"hi"}) | receive({"type":"chunk",...}) → receive({"type":"done"}) |
| W3 | WebSocket 空消息 | ws.send("") | 无响应（跳过空消息） |
| W4 | WebSocket JSON 解析失败 | ws.send("invalid json") | content="invalid json"（当作纯文本） |
| W5 | memory/export 空 | 无 memory 文件 | {"memory_files": {}} |
| W6 | memory/export 有文件 | MEMORY.md + 1 daily | {"memory_files": {"MEMORY.md": "...", "memory/2026-08-02.md": "..."}} |
| W7 | memory/import | {"memory_files": {"MEMORY.md": "content"}} | {"imported": ["MEMORY.md"], "count": 1} |
| W8 | memory/list 空 | 无 memory 文件 | {"files": [], "count": 0} |
| W9 | memory/list 有文件 | 2 daily 文件 | {"files": [...], "count": 2} |
| W10 | memory/search | {"query": "test"} | {"query": "test", "result": "..."} |
| W11 | 503 Agent 未初始化 | 直接调用 export | status_code=503, {"error": "Memory not initialized"} |

---

### 9. CLI Memory Tool (`src/litepaw/memory_tool.py`)

**预期行为：**
- `export` 命令创建 ZIP 文件包含所有 memory 文件
- `import` 命令从 ZIP 文件解压到 workspace
- `list` 命令列出 memory 文件和大小
- `search` 命令关键词搜索 memory 文件内容

**测试用例：**

| ID | 测试名称 | 输入 | 预期输出 |
|----|---------|------|---------|
| T1 | export 空 workspace | workspace 无文件 | "No memory files found" |
| T2 | export 有文件 | MEMORY.md + 1 daily | ZIP 文件包含 2 个文件 |
| T3 | import 新文件 | ZIP 含 MEMORY.md | workspace/MEMORY.md 被创建 |
| T4 | import merge 模式 | 目标已存在，merge=True | 跳过已存在文件 |
| T5 | import overwrite 模式 | 目标已存在，merge=False | 覆盖已存在文件 |
| T6 | list 空 | workspace 无文件 | "No memory files found" |
| T7 | list 有文件 | 2 daily 文件 | 输出 2 行，包含名称和字节数 |
| T8 | search 匹配 | 文件含 "Python" 关键词 | 输出匹配行和上下文 |
| T9 | search 无匹配 | 查询不存在关键词 | "No matches found" |

---

## 测试执行计划

### 阶段 1：单元测试（现有测试扩展）
- 目录：`tests/memory/test_memory.py`
- 添加：Config、ChatAgent、CLI 测试
- 运行：`uv run pytest tests/ -v`

### 阶段 2：集成测试
- 测试 FastAPI TestClient 对 REST 端点的调用
- 测试 WebSocket 端点（使用 TestClient.websocket）
- 运行：`uv run pytest tests/integration/ -v`

### 阶段 3：端到端测试（可选）
- 启动服务 → 发送 WebSocket 消息 → 验证响应
- 运行：`uv run pytest tests/e2e/ -v`

---

## 测试覆盖目标

| 模块 | 当前覆盖 | 目标覆盖 |
|------|---------|---------|
| config/settings.py | 0% | 80% |
| memory/prompts.py | 100% | 100% |
| memory/reme_config.py | 100% | 100% |
| memory/base_memory_manager.py | 0% | 70% |
| memory/reme_light_memory_manager.py | 0% | 70% |
| agent/chat_agent.py | 0% | 70% |
| server/ws_server.py | 0% | 80% |
| memory_tool.py | 0% | 80% |

---

## 执行状态

- [ ] 阶段 1：单元测试
- [ ] 阶段 2：集成测试
- [ ] 阶段 3：端到端测试
