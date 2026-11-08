"""集中管理默认值、环境变量读取和运行时配置。

所有环境变量解析都收敛到这里，业务模块只读取 ``Settings`` 对象，不再各自
调用 ``os.getenv`` 并手写一长串 ``or`` 回退逻辑。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_CONTEXT_WINDOW = 65536
RESERVED_OUTPUT_TOKENS = 2048
RESERVED_TOOL_TOKENS = 4096
RESERVED_FORMAT_OVERHEAD_TOKENS = 512

DEFAULT_MAX_HISTORY_TOKENS = 2500
MAX_SINGLE_MESSAGE_TOKENS = 1200
MAX_MEMORY_SUMMARY_TOKENS = 1200

DEFAULT_USER_ROLE = "项目开发人员"
DEFAULT_SCENE_RULE = "Idea讨论，引导用户聊天，最终生成规格定义器"
DEFAULT_CHAT_TEMPERATURE = 0.7
DEFAULT_UTILITY_TEMPERATURE = 0.0
DEFAULT_CHAT_TIMEOUT_SECONDS = 20
DEFAULT_UTILITY_TIMEOUT_SECONDS = 10
DEFAULT_CHAT_MAX_RETRIES = 1
DEFAULT_UTILITY_MAX_RETRIES = 0
DEFAULT_RECURSION_LIMIT = 8

SUMMARY_MIN_MESSAGES = 4
SUMMARY_DEFERRAL_TOKEN_BUDGET = 800
SUMMARY_MIN_INTERVAL_SECONDS = 5

CLI_THREAD_ID = "session_001"


@dataclass(frozen=True)
class Settings:
    """从进程环境变量解析出的完整运行配置。"""

    api_key: str | None = None
    model: str = DEFAULT_MODEL
    base_url: str | None = None
    utility_model: str | None = None
    user_role: str = DEFAULT_USER_ROLE
    scene_rule: str = DEFAULT_SCENE_RULE
    chat_temperature: float = DEFAULT_CHAT_TEMPERATURE
    utility_temperature: float = DEFAULT_UTILITY_TEMPERATURE
    chat_timeout_seconds: float = DEFAULT_CHAT_TIMEOUT_SECONDS
    utility_timeout_seconds: float = DEFAULT_UTILITY_TIMEOUT_SECONDS
    chat_max_retries: int = DEFAULT_CHAT_MAX_RETRIES
    utility_max_retries: int = DEFAULT_UTILITY_MAX_RETRIES
    max_history_tokens: int | None = None
    context_window: int = DEFAULT_CONTEXT_WINDOW
    recursion_limit: int = DEFAULT_RECURSION_LIMIT
    timing_enabled: bool = False
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None

    def resolve_history_token_budget(self, override: int | None = None) -> int:
        """计算历史窗口预算，并统一扣除输出/工具参数预留空间。"""
        if override is not None:
            return max(1, int(override))
        if self.max_history_tokens is not None:
            return max(1, int(self.max_history_tokens))

        computed = (
            self.context_window
            - RESERVED_OUTPUT_TOKENS
            - RESERVED_TOOL_TOKENS
            - RESERVED_FORMAT_OVERHEAD_TOKENS
        )
        return max(1, min(DEFAULT_MAX_HISTORY_TOKENS, computed))

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """从环境变量构造配置，优先读取新名称，兼容旧的 DeepSeek 变量名。"""
        source = os.environ if env is None else env
        return cls(
            api_key=_optional_text(source, "LLM_API_KEY", "DEEPSEEK_API_KEY"),
            model=_text(
                source,
                "LLM_MODEL",
                "DEEPSEEK_MODEL",
                default=DEFAULT_MODEL,
            ),
            base_url=_optional_text(
                source,
                "LLM_BASE_URL",
                "DEEPSEEK_BASE_URL",
            ),
            utility_model=_optional_text(
                source,
                "LLM_UTILITY_MODEL",
                "SPEC_AGENT_UTILITY_MODEL",
            ),
            user_role=_text(
                source,
                "SPEC_AGENT_USER_ROLE",
                default=DEFAULT_USER_ROLE,
            ),
            scene_rule=_text(
                source,
                "SPEC_AGENT_SCENE_RULE",
                default=DEFAULT_SCENE_RULE,
            ),
            chat_temperature=_float(
                source,
                "SPEC_AGENT_CHAT_TEMPERATURE",
                default=DEFAULT_CHAT_TEMPERATURE,
            ),
            utility_temperature=_float(
                source,
                "SPEC_AGENT_UTILITY_TEMPERATURE",
                default=DEFAULT_UTILITY_TEMPERATURE,
            ),
            chat_timeout_seconds=_float(
                source,
                "SPEC_AGENT_CHAT_TIMEOUT_SECONDS",
                "SPEC_AGENT_CHAT_LLM_TIMEOUT_SECONDS",
                default=DEFAULT_CHAT_TIMEOUT_SECONDS,
            ),
            utility_timeout_seconds=_float(
                source,
                "SPEC_AGENT_UTILITY_TIMEOUT_SECONDS",
                "SPEC_AGENT_UTILITY_LLM_TIMEOUT_SECONDS",
                default=DEFAULT_UTILITY_TIMEOUT_SECONDS,
            ),
            chat_max_retries=_int_required(
                source,
                "SPEC_AGENT_CHAT_MAX_RETRIES",
                "SPEC_AGENT_CHAT_LLM_MAX_RETRIES",
                default=DEFAULT_CHAT_MAX_RETRIES,
            ),
            utility_max_retries=_int_required(
                source,
                "SPEC_AGENT_UTILITY_MAX_RETRIES",
                "SPEC_AGENT_UTILITY_LLM_MAX_RETRIES",
                default=DEFAULT_UTILITY_MAX_RETRIES,
            ),
            max_history_tokens=_int(
                source,
                "SPEC_AGENT_MAX_HISTORY_TOKENS",
                default=None,
            ),
            context_window=_int_required(
                source,
                "LLM_CONTEXT_WINDOW",
                "SPEC_AGENT_CONTEXT_WINDOW",
                default=DEFAULT_CONTEXT_WINDOW,
            ),
            recursion_limit=_int_required(
                source,
                "SPEC_AGENT_RECURSION_LIMIT",
                default=DEFAULT_RECURSION_LIMIT,
            ),
            timing_enabled=_bool(
                source,
                "SPEC_AGENT_TIMING",
                default=False,
            ),
            langsmith_tracing=_bool(
                source,
                "LANGSMITH_TRACING",
                "LANGCHAIN_TRACING_V2",
                default=False,
            ),
            langsmith_api_key=_optional_text(source, "LANGSMITH_API_KEY"),
            langsmith_project=_optional_text(source, "LANGSMITH_PROJECT"),
        )


def _first_text(source: Mapping[str, str], *names: str) -> str | None:
    for name in names:
        value = source.get(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _optional_text(source: Mapping[str, str], *names: str) -> str | None:
    return _first_text(source, *names)


def _text(
    source: Mapping[str, str],
    *names: str,
    default: str,
) -> str:
    value = _first_text(source, *names)
    return default if value is None else value


def _int(
    source: Mapping[str, str],
    *names: str,
    default: int | None,
) -> int | None:
    value = _first_text(source, *names)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _int_required(
    source: Mapping[str, str],
    *names: str,
    default: int,
) -> int:
    value = _first_text(source, *names)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float(
    source: Mapping[str, str],
    *names: str,
    default: float,
) -> float:
    value = _first_text(source, *names)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _bool(
    source: Mapping[str, str],
    *names: str,
    default: bool,
) -> bool:
    value = _first_text(source, *names)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回当前进程环境下的配置，结果会被缓存。"""
    return Settings.from_env()


def load_settings(env_file: str | None = None) -> Settings:
    """加载 ``.env`` 并重建缓存中的配置。"""
    load_dotenv(env_file)
    get_settings.cache_clear()
    return get_settings()
