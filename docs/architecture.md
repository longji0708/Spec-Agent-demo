# 架构说明

## 调用流程

```text
src/__main__.py
        └── cli.main()
                └── agent.create_deepseek_agent()
                        └── OpenAI(base_url=https://api.deepseek.com)
                                └── LangGraph StateGraph
```

## 核心模块

- `src/agent.py`：定义工具 `add`、LangGraph 节点、路由和状态图。
- `src/cli.py`：加载 `.env`，提供交互式命令行。
- `src/__main__.py`：支持通过 `python -m src` 启动。

## 扩展工具

在 `agent.py` 中新增函数、`TOOL_EXECUTORS` 映射和 `TOOLS` 定义即可。
