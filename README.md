# Spec Agent

> 一个使用 LangGraph `StateGraph + ToolNode` 显式构建的 AI 项目规格定义器。
> 它通过 OpenAI 兼容接口调用任意兼容模型，把零散的产品想法逐步收敛成结构化规格，
> 并自动检查缺失项、内部冲突，最终导出 Markdown、HTML 或 Word 文档。

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

## 项目定位

这是一个面向简历展示的智能体项目，重点演示以下工程能力：

- 使用 LangGraph 显式编排 `Agent` 与 `ToolNode`，而不是把核心逻辑藏在黑盒框架里。
- 通过 OpenAI 兼容接口解耦模型供应商，可切换到 DeepSeek、OpenAI、Azure 或其他兼容服务。
- 使用 Pydantic 维护结构化规格状态，并用 Jinja2 和 `python-docx` 生成多格式交付物。
- 实现短期记忆、token 预算、后台摘要、工具异常降级、安全输出路径等生产级细节。
- 支持无 API Key 的本地 Demo 模式，方便面试官或协作者直接跑通完整流程。

## 它能做什么

用户在 CLI 中描述一个项目想法，智能体会逐步追问并抽取以下信息：

- 项目名称
- 目标用户
- 功能需求
- 非功能需求
- 约束条件
- 交付物
- 验证规格
- 技术栈
- 风险

当必填字段完整且没有关键冲突后，可以导出最终规格定义文档。

## 架构图

![Spec Agent 系统架构图](images/architecture.png)

### 核心调用链

```text
CLI / python -m spec_agent
        └── AgentRuntime
                └── LangGraph StateGraph
                        ├── Agent Node
                        │       └── ChatOpenAI（对话模型）
                        ├── ToolNode
                        │       ├── extract_specification
                        │       ├── check_missing_fields
                        │       ├── detect_specification_conflicts
                        │       └── render_specification_document
                        ├── MemorySaver（短期记忆）
                        └── SpecificationStore（内存或 JSON 持久化）
```

## 核心流程

![Spec Agent 核心流程图](images/workflow.png)

多轮对话会形成一个闭环：用户补充信息 → Agent 决定是否需要调用工具 → ToolNode
更新结构化规格 → 返回缺失项或冲突 → 继续追问，直到规格达到可交付状态。

## 输出预览

![Spec Agent 输出预览](images/output-preview.png)

> 上图为模板渲染效果示例，实际内容会根据用户对话逐步填充。

## 核心特性

### 1. 显式的 LangGraph 图结构

项目没有把模型调用、工具调用和状态更新混在一起，而是使用：

- `StateGraph`：定义 Agent 节点和工具节点。
- `ToolNode`：统一执行规格工具。
- `tools_condition`：根据模型是否请求工具来决定路由。
- `MemorySaver`：保存当前会话 checkpoint。

### 2. 模型供应商解耦

使用 `ChatOpenAI` 访问 OpenAI 兼容接口，默认模型为 `gpt-4o-mini`。切换 DeepSeek 只需修改 `.env`：

```dotenv
LLM_API_KEY=sk-your-deepseek-api-key
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
```

对话模型与 utility 模型可以分开配置，抽取和摘要任务默认使用更低温度，便于提高结构化输出稳定性。

### 3. 增量规格抽取

`extract_specification` 每轮从用户输入中抽取**新增或修正信息**，避免旧信息被模型遗漏时丢失。支持：

- 列表字段增量合并；
- 删除已有条目；
- 用户明确覆盖时整体替换列表；
- 对“项目名称叫 X”“技术栈用 A、B”等高确定性短输入做本地快速抽取，减少额外 LLM 调用。

### 4. 缺失项检查与冲突检测

`check_missing_fields` 区分必填字段和推荐字段，并返回追问话术。

`detect_specification_conflicts` 内置常见需求矛盾检查，例如：

- 低成本 vs 高并发；
- 离线可用 vs 实时同步。

### 5. 多格式文档导出

通过 Jinja2 模板和 `python-docx` 生成：

```text
output/default/specification.md
output/default/specification.html
output/default/specification.docx
```

必填字段未完成或存在冲突时，工具会返回 `blocked`；可以通过 `force=true` 强制导出。

### 6. 短期记忆与后台摘要

- 最近消息会完整保留在提示词中。
- 超过 token 窗口的旧消息会被压缩成摘要。
- 回复完成后在后台更新摘要，不阻塞首字流式输出。
- 当前版本只使用进程内 `MemorySaver`，不会写入 `agent_memory.db`。

### 7. 可选 JSON 持久化

默认会话使用内存存储，适合演示和一次性任务。传入 `--storage` 后，规格对象会同步写入 JSON，下次可以继续编辑：

```powershell
spec-agent --storage output/my-project.json --project my-project
```

## 快速开始

### 环境要求

- Python 3.10+

### 1. 配置环境变量

Linux / macOS：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，至少填入 `LLM_API_KEY`。使用 DeepSeek 时额外设置 `LLM_MODEL` 和 `LLM_BASE_URL`。

### 2. 安装

```bash
python -m pip install -e .
```

Windows PowerShell 使用相同命令。`requirements.txt` 仅保留 editable 安装入口，真正的依赖来源是 `pyproject.toml`。

### 3. 启动交互式对话

```bash
spec-agent
```

也可以使用模块方式启动：

```bash
python -m spec_agent
```

输入 `exit`、`quit` 或 `退出` 可以结束程序。

## 无需 API Key 的演示模式

Demo 模式使用本地 Fake LLM，可以快速验证完整 LangGraph 工具流程：

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -X utf8 -m spec_agent --demo --prompt "我想做一个面向产品经理的规格定义工具，支持移动端和离线使用"
```

示例输出：

```text
演示模式已启动，不需要真实 API Key。
输入 exit、quit 或“退出”可以结束对话。

AI：我已经记录下这个示例项目，可以继续补充目标用户和功能需求。
```

正式环境单次调用：

```bash
spec-agent --prompt "我要做一个面向产品经理的规格定义工具"
```

## CLI 参数

| 参数 | 说明 |
| --- | --- |
| `--prompt` | 非交互模式：只处理一条输入后退出 |
| `--demo` | 使用本地 Fake LLM，无需 API Key |
| `--storage PATH` | 规格 JSON 持久化文件路径 |
| `--project ID` | 项目 ID，默认 `default` |

## 规格工具

| 工具 | 作用 | 典型返回值 |
| --- | --- | --- |
| `extract_specification` | 抽取并增量合并用户输入 | 更新状态、Markdown 快照路径、缺失项、冲突项 |
| `check_missing_fields` | 检查必填和推荐字段 | 是否完整、缺失项、追问建议 |
| `detect_specification_conflicts` | 检测规格内部矛盾 | 是否存在冲突、冲突详情、澄清建议 |
| `render_specification_document` | 导出最终文档 | 渲染结果、格式、文件路径，或 `blocked` |

## 输出目录

默认输出目录：

```text
output/
└── default/
    ├── specification.md
    ├── specification.html
    └── specification.docx
```

同一个 `output` 根目录下，不同 `project_id` 会使用独立子目录，避免互相覆盖。

## 环境变量

关键配置如下，完整示例见 [`.env.example`](.env.example)。

| 变量名 | 必填 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 是 | OpenAI 兼容接口的 API Key |
| `LLM_MODEL` | 否 | 对话模型名称，默认 `gpt-4o-mini` |
| `LLM_BASE_URL` | 否 | OpenAI 兼容接口地址 |
| `LLM_UTILITY_MODEL` | 否 | 抽取/摘要工具使用的模型；为空时复用 `LLM_MODEL` |
| `LLM_CONTEXT_WINDOW` | 否 | 用于自动计算历史窗口的上下文窗口大小，默认 `65536` |
| `SPEC_AGENT_USER_ROLE` | 否 | 用户身份提示词，默认 `项目开发人员` |
| `SPEC_AGENT_SCENE_RULE` | 否 | 场景约束提示词 |
| `SPEC_AGENT_MAX_HISTORY_TOKENS` | 否 | 历史窗口 token 上限，默认按上下文窗口自动计算 |
| `SPEC_AGENT_RECURSION_LIMIT` | 否 | 单轮图递归上限，默认 `4` |
| `SPEC_AGENT_TIMING` | 否 | 设为 `1` 时输出分阶段耗时日志 |
| `LANGSMITH_TRACING` | 否 | 设为 `true` 时启用 LangSmith 追踪 |
| `LANGSMITH_API_KEY` | 否 | LangSmith API Key |
| `LANGSMITH_PROJECT` | 否 | LangSmith 项目名称 |

温度、超时、重试等参数请参考 `.env.example`。旧版 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL` 以及部分 `SPEC_AGENT_*_LLM_*` 变量仍会兼容，但建议迁移到上表中的新名称。

## 项目结构

```text
.
├── .env.example
├── .github/
│   └── workflows/ci.yml
├── docs/
│   └── architecture.md
├── images/
│   ├── architecture.png
│   ├── workflow.png
│   ├── output-preview.png
│   └── README.md
├── src/
│   └── spec_agent/
│       ├── __init__.py
│       ├── __main__.py
│       ├── agent.py
│       ├── runtime.py
│       ├── llm.py
│       ├── graph.py
│       ├── memory.py
│       ├── tokenizer.py
│       ├── history_window.py
│       ├── message_sanitizer.py
│       ├── summarizer.py
│       ├── messages.py
│       ├── prompts.py
│       ├── config.py
│       ├── chat_ui.py
│       ├── demo.py
│       ├── cli.py
│       └── tools/
│           ├── schemas.py
│           ├── store.py
│           ├── extraction.py
│           ├── validation.py
│           ├── conflicts.py
│           ├── rendering.py
│           ├── registry.py
│           └── templates/
│               ├── specification.md.j2
│               └── specification.html.j2
├── tests/
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

## 开发与测试

安装开发依赖：

```bash
python -m pip install -e ".[dev]"
```

运行测试和覆盖率：

```bash
python -m pytest --cov=spec_agent --cov-report=term-missing
```

代码检查与类型检查：

```bash
ruff check src tests
mypy src
```

CI 会使用 Python 3.10 和 3.11 运行 `ruff`、`mypy` 与 pytest，并要求测试覆盖率不低于 70%。

## 扩展方式

新增规格工具时，建议保持“纯逻辑服务 + 工具包装”的边界：

1. 在 `tools/` 中实现纯 Python 业务逻辑；
2. 在 `tools/registry.py` 的 `build_specification_toolkit()` 中注册为 LangChain 工具；
3. 在 `runtime.py` 中完成依赖注入；
4. 如有新的结构化字段，同步更新 `tools/schemas.py` 和渲染模板。

## 图片与截图说明

仓库图片统一放在 [`images/`](images/) 中。目前已经生成的展示图：

- `images/architecture.png`：中文系统架构图；
- `images/workflow.png`：从想法到文档的核心流程闭环；
- `images/output-preview.png`：规格定义文档的输出预览示例。

建议继续补充以下真实截图，具体命名和内容要求见 [`images/README.md`](images/README.md)：

- CLI 交互或 Demo 模式截图；
- LangSmith 链路追踪截图；
- 真实会话生成的最终 Markdown/HTML/Word 文档截图；
- 测试或 CI 运行结果截图。

## Roadmap

- 增加 Web UI，让产品经理无需接触命令行；
- 支持多个项目会话管理与历史记录恢复；
- 引入更强的记忆层，例如向量检索或数据库持久化；
- 增加更丰富的规格字段和行业模板；
- 提供 FastAPI 接口，将规格智能体封装为服务。

## License

[MIT](LICENSE)
