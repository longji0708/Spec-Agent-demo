# Spec Agent - AI 项目规格定义器

一个使用 LangGraph `StateGraph + ToolNode` 显式构建的智能体，
通过 OpenAI 兼容接口调用任意兼容模型，并支持 LangSmith 链路追踪。

## 目录结构

```text
.
├── .env.example          # 环境变量示例
├── requirements.txt      # 依赖清单
├── pyproject.toml        # 项目元数据、打包与开发工具配置
├── README.md
├── .github/
│   └── workflows/ci.yml  # CI 检查
├── src/
│   ├── __init__.py
│   ├── __main__.py       # 命令行入口
│   ├── agent.py          # 智能体 API 门面
│   ├── runtime.py        # 智能体运行时装配
│   ├── llm.py            # OpenAI 兼容模型创建与 LangSmith 配置
│   ├── graph.py          # LangGraph 图、节点和路由定义
│   ├── memory.py         # 短期记忆门面
│   ├── tokenizer.py      # token 估算
│   ├── history_window.py # 最近消息窗口切分
│   ├── message_sanitizer.py # 消息序列清洗
│   ├── summarizer.py     # 历史消息摘要
│   ├── messages.py       # 消息文本转换
│   ├── prompts.py        # 系统提示词
│   ├── config.py         # 默认配置
│   ├── chat_ui.py        # 命令行配色与流式输出
│   ├── tools/            # 工具定义与注册
│   │   ├── __init__.py
│   │   ├── schemas.py    # Pydantic 规格模型
│   │   ├── store.py      # 会话内规格存储
│   │   ├── extraction.py # 信息抽取与增量合并
│   │   ├── validation.py # 缺失字段检查
│   │   ├── conflicts.py  # 规格冲突检测
│   │   ├── rendering.py  # Markdown/HTML/Word 渲染
│   │   ├── registry.py   # LangChain 工具装配
│   │   └── templates/
│   │       ├── specification.md.j2
│   │       └── specification.html.j2
│   └── cli.py            # 交互式命令行
├── docs/
│   └── architecture.md   # 架构说明
└── tests/
    ├── test_agent.py     # 单元测试
    ├── test_memory.py    # 短期记忆单元测试
    ├── test_chat_ui.py   # 流式输出单元测试
    └── test_specification_tools.py  # 规格工具单元测试
```

## 快速开始

```powershell
# 1. 配置 OpenAI 兼容接口
Copy-Item .env.example .env
# 编辑 .env，至少填入 LLM_API_KEY。
# 使用 DeepSeek 时额外设置 LLM_MODEL=deepseek-chat 和 LLM_BASE_URL=https://api.deepseek.com

# 2. 安装依赖（requirements.txt 只是 editable 安装入口，依赖唯一来源是 pyproject.toml）
python -m pip install -e .

# 3. 启动
python -m src
```

输入 `exit`、`quit` 或 `退出` 可以结束程序。

## 规格定义工具

智能体会在对话中逐步抽取需求，并保存为结构化规格对象：

- `extract_specification`：每轮对话后抽取自然语言需求，增量更新规格对象，并保存 Markdown 快照，同时返回缺失字段和冲突。
- `check_missing_fields`：检查必填字段，返回缺失项和追问话术。
- `detect_specification_conflicts`：检查低成本 vs 高并发、离线可用 vs 实时同步等内部矛盾。
- `render_specification_document`：在必填字段完整且无关键冲突时生成最终的 Markdown、HTML 或 Word 规格定义文档；否则返回 blocked，可通过 `force=true` 强制导出。

默认输出目录是项目根目录下的 `output/`，最终文件为：

```text
output/specification.md
output/specification.html
output/specification.docx
```

## 记忆机制

会话只使用短期记忆。LangGraph 使用 `MemorySaver` 作为 checkpointer，
不会写入 `agent_memory.db`。最近的消息会完整保留在提示词中，超出 token
窗口的旧消息会被压缩成摘要；程序或命令行窗口退出后，这些消息和摘要都会
随进程释放，不会保留到下一次启动。

## 运行测试

```powershell
python -m unittest discover -s tests
```

## 环境变量

| 变量名 | 必填 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 是 | OpenAI 兼容接口的 API Key |
| `LLM_MODEL` | 否 | 对话模型名称，默认 `gpt-4o-mini` |
| `LLM_BASE_URL` | 否 | OpenAI 兼容接口地址；为空时使用 ChatOpenAI 默认地址 |
| `LLM_UTILITY_MODEL` | 否 | 抽取/摘要工具使用的模型；为空时复用 `LLM_MODEL` |
| `LLM_CONTEXT_WINDOW` | 否 | 用于自动计算历史窗口的上下文窗口大小，默认 `65536` |
| `SPEC_AGENT_USER_ROLE` | 否 | 用户身份提示词，默认 `项目开发人员` |
| `SPEC_AGENT_SCENE_RULE` | 否 | 场景约束提示词，默认 `Idea讨论...` |
| `SPEC_AGENT_CHAT_TEMPERATURE` | 否 | 对话模型温度，默认 `0.7` |
| `SPEC_AGENT_UTILITY_TEMPERATURE` | 否 | 抽取/摘要工具温度，默认 `0.0` |
| `SPEC_AGENT_MAX_HISTORY_TOKENS` | 否 | 历史窗口 token 上限，默认按上下文窗口自动计算 |
| `SPEC_AGENT_CHAT_TIMEOUT_SECONDS` | 否 | 对话模型超时秒数，默认 `20` |
| `SPEC_AGENT_UTILITY_TIMEOUT_SECONDS` | 否 | 工具/摘要模型超时秒数，默认 `10` |
| `SPEC_AGENT_CHAT_MAX_RETRIES` | 否 | 对话模型重试次数，默认 `1` |
| `SPEC_AGENT_UTILITY_MAX_RETRIES` | 否 | 工具/摘要模型重试次数，默认 `0` |
| `SPEC_AGENT_RECURSION_LIMIT` | 否 | 单轮图递归上限，默认 `4` |
| `SPEC_AGENT_TIMING` | 否 | 设为 `1` 时输出分阶段耗时日志 |
| `LANGSMITH_TRACING` | 否 | 设为 `true` 时启用 LangSmith 追踪 |
| `LANGSMITH_API_KEY` | 否 | LangSmith API Key |
| `LANGSMITH_PROJECT` | 否 | LangSmith 项目名称 |

旧版 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL` 以及
`SPEC_AGENT_*_LLM_*` 变量仍会被识别，但建议迁移到上表中的新名称。
