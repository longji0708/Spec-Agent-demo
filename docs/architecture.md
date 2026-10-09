# 架构说明

## 调用流程

```text
src/__main__.py
        └── cli.main()
                └── agent.create_deepseek_agent()
                        └── LangGraph StateGraph
                                └── ChatOpenAI(base_url=https://api.deepseek.com)
                                        └── LangSmith 追踪
```

## 核心模块

- `src/agent.py`：使用 `StateGraph + ToolNode + tools_condition` 显式定义节点、路由和编译图，并启用 LangSmith 追踪。
- `src/tools.py`：使用 LangChain `@tool` 定义可供模型调用的工具。
- `src/cli.py`：加载 `.env`，提供交互式命令行。
- `src/__main__.py`：支持通过 `python -m src` 启动。

## 扩展工具

在 `src/tools.py` 中新增一个 `@tool` 函数，并把它加入 `TOOLS` 列表即可。
`src/agent.py` 中的 `ToolNode(TOOLS)` 会自动把工具接到执行图中。
