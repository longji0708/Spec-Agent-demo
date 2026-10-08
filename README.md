# DeepSeek LangGraph 智能体

一个最简的 LangGraph 智能体，通过 OpenAI 兼容接口调用 DeepSeek 的 `deepseek-chat` 模型。

## 目录结构

```text
.
├── .env.example          # 环境变量示例
├── requirements.txt      # 依赖清单
├── README.md
├── src/
│   ├── __init__.py
│   ├── __main__.py       # 命令行入口
│   ├── agent.py          # 智能体与工具定义
│   └── cli.py            # 交互式命令行
├── docs/
│   └── architecture.md   # 架构说明
└── tests/
    └── test_agent.py     # 单元测试
```

## 快速开始

```powershell
# 1. 创建虚拟环境
python -m venv .venv

# 2. 安装依赖
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. 配置 DeepSeek API Key
Copy-Item .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY

# 4. 启动
.\.venv\Scripts\python.exe -m src
```

输入 `exit`、`quit` 或 `退出` 可以结束程序。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 环境变量

| 变量名 | 必填 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 是 | DeepSeek 开放平台 API Key |
| `DEEPSEEK_MODEL` | 否 | 使用的模型名称，默认 `deepseek-chat` |
