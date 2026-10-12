# 架构说明

## 调用流程

```text
src/__main__.py
        └── cli.main()
                └── agent.create_deepseek_agent()
                        ├── ChatOpenAI(base_url=https://api.deepseek.com)
                        └── graph.build_agent_graph()
                                ├── LangGraph StateGraph
                                │   ├── Agent 节点
                                │   └── ToolNode 工具节点
                                ├── MemorySaver（短期记忆）
                                └── LangSmith 追踪
```

## 核心模块

- `src/agent.py`：读取 DeepSeek 配置，创建带工具绑定的模型和摘要模型。
- `src/graph.py`：使用 `StateGraph + ToolNode + tools_condition` 定义节点、路由和编译图。
- `src/memory.py`：管理最近消息窗口和旧消息摘要，使用内存 checkpointer 实现短期记忆。
- `src/prompts.py`：根据当前用户角色、场景约束和摘要生成系统提示词。
- `src/tools/`：使用 LangChain `@tool` 定义可供模型调用的工具。
- `src/cli.py`：加载 `.env`，提供交互式命令行。
- `src/__main__.py`：支持通过 `python -m src` 启动。

## 扩展工具

在 `src/tools/basic.py` 中新增一个 `@tool` 函数，并把它加入 `TOOLS` 列表即可。
`src/graph.py` 中的 `ToolNode(TOOLS)` 会自动把工具接到执行图中。
