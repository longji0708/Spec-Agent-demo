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
│   ├── agent.py          # LangGraph 图、节点和路由定义
│   ├── tools.py          # 工具定义
│   └── cli.py            # 交互式命令行
├── docs/
│   └── architecture.md   # 架构说明
└── tests/
    └── test_agent.py     # 单元测试
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
