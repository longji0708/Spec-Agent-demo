"""集中管理默认配置和提示词所使用的环境变量键。"""

from __future__ import annotations

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"

# 保留在提示词中的最近消息 token 上限，超过部分会进入摘要。
MAX_HISTORY_TOKENS = 2500

DEFAULT_USER_ROLE = "项目开发人员"
DEFAULT_SCENE_RULE = "Idea讨论，引导用户聊天，最终生成规格定义器"

# 对话模型使用稍高的随机性，让回复更像自然交流；
# 抽取和摘要等工具任务保持确定性，避免把规格写乱。
CHAT_TEMPERATURE = 0.7
UTILITY_TEMPERATURE = 0.0

# 当前只提供命令行会话，使用固定线程 ID 即可。
# 由于 checkpointer 是 MemorySaver，进程退出后该会话会自然消失。
CLI_THREAD_ID = "session_001"
