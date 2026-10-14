# DeepSeek LangGraph 智能体

一个使用 LangGraph `StateGraph + ToolNode` 显式构建的 DeepSeek 智能体，
通过 OpenAI 兼容接口调用 DeepSeek，并支持 LangSmith 链路追踪。

## 目录结构

```text
.
├── .env.example          # 环境变量示例
├── requirements.txt      # 依赖清单
├── README.md
├── src/
│   ├── __init__.py
│   ├── __main__.py       # 命令行入口
│   ├── agent.py          # 智能体工厂：读取配置并创建模型
│   ├── graph.py          # LangGraph 图、节点和路由定义
│   ├── memory.py         # 摘要式短期记忆
│   ├── prompts.py        # 系统提示词
│   ├── config.py         # 默认配置
│   ├── chat_ui.py        # 命令行配色与流式输出
│   ├── tools/            # 工具定义与注册
│   │   ├── __init__.py
│   │   ├── basic.py
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
# 1. 在已有 conda 环境中安装依赖
python -m pip install -r requirements.txt

# 2. 配置 DeepSeek API Key
Copy-Item .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY 和 LangSmith 配置

# 3. 启动
python -m src
```

输入 `exit`、`quit` 或 `退出` 可以结束程序。

## 规格定义工具

智能体会在对话中逐步抽取需求，并保存为结构化规格对象：

- `extract_specification`：每轮对话后抽取自然语言需求，增量更新规格对象，并保存 `specification.md` 快照。
- `check_missing_fields`：检查必填字段，返回缺失项和追问话术。
- `detect_specification_conflicts`：检查低成本 vs 高并发、离线可用 vs 实时同步等内部矛盾。
- `render_specification_document`：生成最终的 Markdown、HTML 或 Word 规格定义文档。

默认输出目录是项目根目录，最终文件为：

```text
specification.md
specification.html
specification.docx
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
| `DEEPSEEK_API_KEY` | 是 | DeepSeek 开放平台 API Key |
| `DEEPSEEK_MODEL` | 否 | 使用的模型名称，默认 `deepseek-chat` |
| `DEEPSEEK_BASE_URL` | 否 | OpenAI 兼容接口地址，默认 `https://api.deepseek.com` |
| `LANGSMITH_TRACING` | 否 | 设为 `true` 时启用 LangSmith 追踪 |
| `LANGSMITH_API_KEY` | 否 | LangSmith API Key |
| `LANGSMITH_PROJECT` | 否 | LangSmith 项目名称 |
