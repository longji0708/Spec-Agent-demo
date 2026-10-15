# 架构说明

## 调用流程

```text
src/__main__.py
        └── cli.main()
                └── runtime.create_agent()
                        ├── llm.create_chat_llm()
                        ├── llm.create_utility_llm()
                        └── graph.build_agent_graph()
                                ├── LangGraph StateGraph
                                │   ├── Agent 节点
                                │   └── ToolNode 工具节点
                                │       ├── extract_specification
                                │       ├── check_missing_fields
                                │       ├── detect_specification_conflicts
                                │       └── render_specification_document
                                ├── MemorySaver（短期记忆）
                                └── LangSmith 追踪
```

## 核心模块

- `src/agent.py`：智能体 API 门面，保持对外调用入口稳定。
- `src/runtime.py`：装配 LLM、规格存储、工具和图。
- `src/llm.py`：通过 OpenAI 兼容接口创建对话模型和工具模型，并处理 LangSmith 配置。
- `src/graph.py`：使用 `StateGraph + ToolNode + tools_condition` 定义节点、路由和编译图。
- `src/memory.py`：短期记忆门面，组合窗口切分、摘要和状态。
- `src/tokenizer.py`：估算消息 token。
- `src/history_window.py`：维护最近消息窗口。
- `src/message_sanitizer.py`：清洗非法工具消息序列。
- `src/summarizer.py`：压缩历史消息。
- `src/messages.py`：统一处理消息内容到文本的转换。
- `src/prompts.py`：根据当前用户角色、场景约束和摘要生成系统提示词。
- `src/chat_ui.py`：提供 CLI 配色、消息前缀和逐字流式输出。
- `src/tools/schemas.py`：使用 Pydantic 定义规格对象和增量更新模型。
- `src/tools/store.py`：保存当前会话的规格对象。
- `src/tools/extraction.py`：把自然语言抽取为结构化信息并增量合并。
- `src/tools/validation.py`：检查缺失字段并生成追问话术。
- `src/tools/conflicts.py`：检测规格内部矛盾。
- `src/tools/rendering.py`：使用 Jinja2 和 python-docx 渲染文档。
- `src/tools/registry.py`：把纯逻辑服务包装为 LangChain 工具。
- `src/cli.py`：加载 `.env`，提供交互式命令行。
- `src/__main__.py`：支持通过 `python -m src` 启动。

## 扩展工具

依赖会话状态或 LLM 的规格工具，在 `src/tools/registry.py` 的
`build_specification_toolkit()` 中注册，由 `src/runtime.py` 统一绑定到模型。
