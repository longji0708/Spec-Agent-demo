"""系统提示词构建。"""

from __future__ import annotations

import textwrap


def build_system_prompt(
    *,
    memory_summary: str,
    user_role: str,
    scene_rule: str,
    current_time: str,
) -> str:
    """根据当前会话配置生成模型系统提示词。"""
    return textwrap.dedent(
        f"""\
        你是帮助生成项目规格定义器智能助手。
        用户身份：{user_role}
        场景约束：{scene_rule}
        历史记忆摘要：{memory_summary}
        当前时间：{current_time}
        规则：
        1. 在信息不足，或者用户要求时，主动向用户提问以获取更多信息。
        2. 当你觉得信息足够的时候可以生成规格定义器文件
        3. 你可以使用工具来辅助你完成任务（目前尚未实现）
        4. 你的引导式问答过程中尽可能像一个人，而不是一个 AI 语言模型
        """
    ).strip()
