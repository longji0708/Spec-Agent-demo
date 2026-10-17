# 架构说明

## 调用流程

```text
src/spec_agent/__main__.py
        └── spec_agent.cli.main()
                └── spec_agent.runtime.create_agent()
                        ├── spec_agent.llm.create_chat_llm()
                        ├── spec_agent.llm.create_utility_llm()
                        └── spec_agent.graph.build_agent_graph()
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

- `spec_agent/agent.py`：智能体 API 门面，保持对外调用入口稳定。
- `spec_agent/runtime.py`：装配 LLM、规格存储、工具和图。
- `spec_agent/llm.py`：通过 OpenAI 兼容接口创建对话模型和工具模型，并处理 LangSmith 配置。
- `spec_agent/graph.py`：使用 `StateGraph + ToolNode + tools_condition` 定义节点、路由和编译图。
- `spec_agent/memory.py`：短期记忆门面，组合窗口切分、摘要和状态。
- `spec_agent/tokenizer.py`：估算消息 token。
- `spec_agent/history_window.py`：维护最近消息窗口。
- `spec_agent/message_sanitizer.py`：清洗非法工具消息序列。
- `spec_agent/summarizer.py`：压缩历史消息。
- `spec_agent/messages.py`：统一处理消息内容到文本的转换。
- `spec_agent/prompts.py`：根据当前用户角色、场景约束和摘要生成系统提示词。
- `spec_agent/chat_ui.py`：提供 CLI 配色、消息前缀和逐字流式输出。
- `spec_agent/demo.py`：提供无需 API Key 的本地 Fake LLM，用于演示和端到端测试。
- `spec_agent/tools/schemas.py`：使用 Pydantic 定义规格对象和增量更新模型。
- `spec_agent/tools/store.py`：保存当前会话的规格对象，并支持可选 JSON 持久化。
- `spec_agent/tools/extraction.py`：把自然语言抽取为结构化信息并增量合并。
- `spec_agent/tools/validation.py`：检查缺失字段并生成追问话术。
- `spec_agent/tools/conflicts.py`：检测规格内部矛盾。
- `spec_agent/tools/rendering.py`：使用 Jinja2 和 python-docx 渲染文档。
- `spec_agent/tools/registry.py`：把纯逻辑服务包装为 LangChain 工具。
- `spec_agent/cli.py`：加载 `.env`，提供交互式命令行。
- `spec_agent/__main__.py`：支持通过 `python -m spec_agent` 启动。

## 扩展工具

依赖会话状态或 LLM 的规格工具，在 `spec_agent/tools/registry.py` 的
`build_specification_toolkit()` 中注册，由 `spec_agent/runtime.py` 统一绑定到模型。
