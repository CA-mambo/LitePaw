# LitePaw 测试计划（真实 API 版）

## 测试概览

本文档记录 LitePaw 各模块在**真实 API 环境**下的预期行为、测试设计和执行状态。

**API 配置**：从 `.env` 文件加载 DashScope API 密钥
**测试环境**：Python 3.13 + reme-ai==0.4.1.3 + agentscope

---

## 执行状态

| 阶段 | 状态 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 单元测试 | ✅ 完成 | 38 | 0 | 0 |
| 集成测试（真实 API） | ✅ 完成 | 4 | 0 | 0 |
| **总计** | **✅** | **42** | **0** | **1** |

---

## 模块测试（真实 API 验证）

### 1. Config 模块 — 6/6 通过 ✅

| ID | 测试 | 状态 | 备注 |
|----|------|------|------|
| C1 | 默认初始化 | ✅ | Settings() 正确初始化 |
| C2 | YAML 加载 | ✅ | 从 YAML 文件加载配置 |
| C3 | YAML 序列化 | ✅ | 序列化后再加载一致 |
| C4 | 环境变量加载 | ✅ | 从 .env 文件读取 LITEPAW_* |
| C5 | LLMConfig 默认值 | ✅ | model="qwen-plus" |
| C6 | MemoryConfig 默认值 | ✅ | backend="remelight" |

### 2. Memory Prompts — 3/3 通过 ✅

| ID | 测试 | 状态 |
|----|------|------|
| P1 | 中文提示词 | ✅ |
| P2 | 英文提示词 | ✅ |
| P3 | 回退行为 | ✅ |

### 3. ReMe Config — 5/5 通过 ✅

| ID | 测试 | 状态 |
|----|------|------|
| R1 | 基础配置 | ✅ |
| R2 | Embedding 禁用 | ✅ |
| R3 | Embedding 启用 (OpenAI) | ✅ |
| R4 | Embedding 启用 (DashScope) | ✅ |
| R5 | 深拷贝验证 | ✅ |

### 4. Memory Files — 3/3 通过 ✅

| ID | 测试 | 状态 |
|----|------|------|
| F1 | MEMORY.md 读写 | ✅ |
| F2 | daily 文件列出 | ✅ |
| F3 | 中文编码 | ✅ |

### 5. Base Memory Manager — 已补充 ✅

- ✅ 添加 `_shutdown_summarize_worker()` 方法
- ✅ `add_summarize_task()` 任务队列
- ✅ `_summarize_worker()` 串行处理

### 6. ReMeLight Memory Manager — 集成测试验证 ✅

| ID | 测试 | 状态 | 真实 API |
|----|------|------|----------|
| M1 | 初始化 | ✅ | reme-ai==0.4.1.3 正确加载 |
| M2 | start 成功 | ✅ | 调用 ReMe.start() |
| M3 | close 清理 | ✅ | _shutdown_summarize_worker 正常 |
| M4 | get_memory_prompt | ✅ | 返回中文引导词 |
| M5 | memory_search 空查询 | ✅ | 返回错误提示 |
| M6 | memory_search ReMe 未启动 | ✅ | 返回 "ReMe is not started." |
| M7 | summarize 空消息 | ✅ | 返回空字符串 |
| **I1** | **真实 API 搜索** | **✅** | **DashScope API 正常** |
| **I2** | **真实 API 总结** | **✅** | **LLM 生成总结** |

### 7. Chat Agent — 7/7 通过 ✅

| ID | 测试 | 状态 |
|----|------|------|
| A1 | 初始化 | ✅ |
| A2 | 重复初始化 | ✅ |
| A3 | 对话流式输出 | ✅ |
| A4 | 记忆检索 | ✅ |
| A5 | 历史累积 | ✅ |
| A6 | 历史截断 | ✅ |
| A7 | LLM 异常 | ✅ |
| A8 | close 清理 | ✅ |
| **I3** | **真实 API 初始化** | **✅** |

### 8. WebSocket Server — 7/7 通过 + 1 跳过 ✅

| ID | 测试 | 状态 |
|----|------|------|
| W1 | create_app | ✅ |
| W2 | WebSocket 连接 | ⏭️ 跳过（需运行服务） |
| W5 | memory/export 空 | ✅ |
| W6 | memory/export 有文件 | ✅ |
| W7 | memory/import | ✅ |
| W8 | memory/list 空 | ✅ |
| W9 | memory/list 有文件 | ✅ |
| W10 | memory/search | ✅ |

### 9. CLI Memory Tool — 9/9 通过 ✅

| ID | 测试 | 状态 |
|----|------|------|
| T1 | export 空 | ✅ |
| T2 | export 有文件 | ✅ |
| T3 | import 新文件 | ✅ |
| T4 | import merge 跳过 | ✅ |
| T5 | import overwrite | ✅ |
| T6 | list 空 | ✅ |
| T7 | list 有文件 | ✅ |
| T8 | search 匹配 | ✅ |
| T9 | search 无匹配 | ✅ |

---

## 关键修复记录

| 问题 | 修复 |
|------|------|
| `DashScopeFormatter` 不存在 | → `DashScopeChatFormatter` |
| `Msg` 构造函数变更 | → keyword 参数 + `TextBlock` 列表 |
| CLI 命令名冲突 | → `list-memory`/`search-memory`/`import-memory` |
| CLI merge 逻辑反 | → `if merge and target.exists()` |
| ReMe 包错误 | → `reme-ai==0.4.1.3` |
| ReMe 导入路径 | → `from reme import ReMe` |
| `_shutdown_summarize_worker` 缺失 | → 添加到 BaseMemoryManager |

---

## 运行测试

```bash
# 全部测试
uv run pytest tests/ -v

# 仅集成测试（真实 API）
uv run pytest tests/integration/ -v

# 仅单元测试
uv run pytest tests/ -v --ignore=tests/integration/
```

---

## 环境要求

```
Python >= 3.11
reme-ai == 0.4.1.3
agentscope >= 0.1.0
DashScope API key (.env 文件)
```
