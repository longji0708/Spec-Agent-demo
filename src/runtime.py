"""智能体运行时装配。"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from .config import (
    DEFAULT_RECURSION_LIMIT,
    MAX_MEMORY_SUMMARY_TOKENS,
    MAX_SINGLE_MESSAGE_TOKENS,
    SUMMARY_DEFERRAL_TOKEN_BUDGET,
    SUMMARY_MIN_INTERVAL_SECONDS,
    SUMMARY_MIN_MESSAGES,
    get_settings,
)
from .graph import build_agent_graph
from .llm import create_chat_llm, create_utility_llm
from .memory import build_memory_context
from .timing import phase
from .tools import SpecificationStore, build_specification_toolkit


class AgentRuntime:
    """给编译后的 LangGraph 增加流式配置和后台摘要收尾能力。"""

    def __init__(
        self,
        graph: Any,
        summary_model: Any,
        max_history_tokens: int,
        recursion_limit: int = DEFAULT_RECURSION_LIMIT,
    ) -> None:
        self._graph = graph
        self._summary_model = summary_model
        self._max_history_tokens = max_history_tokens
        self._recursion_limit = recursion_limit
        self._summary_lock = threading.Lock()
        self._last_summary_at = 0.0

    def get_graph(self) -> Any:
        return self._graph

    def _with_recursion_limit(self, config: dict[str, Any] | None) -> dict[str, Any]:
        resolved = dict(config or {})
        resolved["recursion_limit"] = resolved.get(
            "recursion_limit",
            self._recursion_limit,
        )
        return resolved

    def stream(self, input: Any, config: dict[str, Any] | None = None, **kwargs: Any):
        return self._graph.stream(input, config=self._with_recursion_limit(config), **kwargs)

    def astream(self, input: Any, config: dict[str, Any] | None = None, **kwargs: Any):
        return self._graph.astream(input, config=self._with_recursion_limit(config), **kwargs)

    def astream_events(
        self,
        input: Any,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        return self._graph.astream_events(
            input,
            config=self._with_recursion_limit(config),
            **kwargs,
        )

    def get_state(self, config: dict[str, Any]) -> Any:
        return self._graph.get_state(config)

    def update_state(self, config: dict[str, Any], values: dict[str, Any]) -> Any:
        return self._graph.update_state(config, values)

    def finalize_memory(self, config: dict[str, Any]) -> None:
        """在回复完成后后台更新摘要，不阻塞首字输出。"""
        if not self._summary_lock.acquire(blocking=False):
            return
        try:
            now = time.monotonic()
            if now - self._last_summary_at < SUMMARY_MIN_INTERVAL_SECONDS:
                return

            self._update_memory_summary(config)
            self._last_summary_at = time.monotonic()
        finally:
            self._summary_lock.release()

    def _update_memory_summary(self, config: dict[str, Any]) -> None:
        with phase("background_summary"):
            snapshot = self._graph.get_state(config)
            values = snapshot.values or {}
            context = build_memory_context(
                messages=values.get("messages", []),
                current_summary=values.get("memory_summary", ""),
                summarized_count=values.get("summarized_count", 0),
                last_summarized_message_id=values.get("last_summarized_message_id"),
                max_tokens=self._max_history_tokens,
                max_single_message_tokens=MAX_SINGLE_MESSAGE_TOKENS,
                max_summary_tokens=MAX_MEMORY_SUMMARY_TOKENS,
                summary_llm=self._summary_model,
                summarize=True,
                min_summary_messages=SUMMARY_MIN_MESSAGES,
                summary_token_budget=SUMMARY_DEFERRAL_TOKEN_BUDGET,
            )
            self._graph.update_state(
                config,
                {
                    "memory_summary": context["memory_summary"],
                    "summarized_count": context["summarized_count"],
                    "last_summarized_message_id": context["last_summarized_message_id"],
                },
            )


def create_agent(
    api_key: str | None = None,
    model_name: str | None = None,
    utility_model_name: str | None = None,
    spec_store: SpecificationStore | None = None,
    output_dir: str | Path | None = None,
    user_role: str | None = None,
    scene_rule: str | None = None,
    chat_temperature: float | None = None,
    utility_temperature: float | None = None,
    max_history_tokens: int | None = None,
    llm_timeout: float | None = None,
    llm_max_retries: int | None = None,
    base_url: str | None = None,
) -> Any:
    """创建带规格定义工具的智能体。"""
    settings = get_settings()
    utility_llm = create_utility_llm(
        api_key=api_key,
        model_name=utility_model_name,
        base_url=base_url,
        temperature=utility_temperature,
        timeout=llm_timeout,
        max_retries=llm_max_retries,
    )
    chat_llm = create_chat_llm(
        api_key=api_key,
        model_name=model_name,
        base_url=base_url,
        temperature=chat_temperature,
        timeout=llm_timeout,
        max_retries=llm_max_retries,
    )

    store = spec_store or SpecificationStore(output_dir=output_dir)
    tools = build_specification_toolkit(store=store, llm=utility_llm)
    model = chat_llm.bind_tools(tools)
    resolved_max_history_tokens = settings.resolve_history_token_budget(
        max_history_tokens
    )
    resolved_user_role = user_role if user_role is not None else settings.user_role
    resolved_scene_rule = scene_rule if scene_rule is not None else settings.scene_rule

    graph = build_agent_graph(
        model=model,
        summary_model=utility_llm,
        tools=tools,
        default_user_role=resolved_user_role,
        default_scene_rule=resolved_scene_rule,
        max_history_tokens=resolved_max_history_tokens,
    )
    return AgentRuntime(
        graph,
        utility_llm,
        resolved_max_history_tokens,
        settings.recursion_limit,
    )
