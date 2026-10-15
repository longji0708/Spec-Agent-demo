"""OpenAI 兼容接口的模型创建与 LangSmith 配置。"""

from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI

from .config import Settings, get_settings


def enable_langsmith_tracing(settings: Settings | None = None) -> None:
    resolved_settings = settings if settings is not None else get_settings()
    if not resolved_settings.langsmith_tracing:
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"


def create_base_llm(
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
    temperature: float = 0,
    timeout: float | None = None,
    max_retries: int | None = None,
    tags: list[str] | None = None,
) -> ChatOpenAI:
    settings = get_settings()
    enable_langsmith_tracing(settings)

    resolved_api_key = api_key if api_key is not None else settings.api_key
    if not resolved_api_key:
        raise ValueError("缺少 LLM_API_KEY，请在 .env 中配置或传入 api_key。")

    resolved_model_name = model_name if model_name is not None else settings.model
    resolved_base_url = base_url if base_url is not None else settings.base_url

    llm_kwargs: dict[str, Any] = {
        "api_key": resolved_api_key,
        "model": resolved_model_name,
        "temperature": temperature,
        "timeout": timeout,
        "max_retries": max_retries,
        "streaming": True,
        "tags": tags,
    }
    if resolved_base_url:
        llm_kwargs["base_url"] = resolved_base_url

    return ChatOpenAI(**llm_kwargs)


def create_chat_llm(
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> ChatOpenAI:
    settings = get_settings()
    return create_base_llm(
        api_key=api_key,
        model_name=model_name,
        base_url=base_url,
        temperature=temperature
        if temperature is not None
        else settings.chat_temperature,
        timeout=timeout
        if timeout is not None
        else settings.chat_timeout_seconds,
        max_retries=max_retries
        if max_retries is not None
        else settings.chat_max_retries,
        tags=["chat_model"],
    )


def create_utility_llm(
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> ChatOpenAI:
    settings = get_settings()
    return create_base_llm(
        api_key=api_key,
        model_name=model_name if model_name is not None else settings.utility_model,
        base_url=base_url,
        temperature=temperature
        if temperature is not None
        else settings.utility_temperature,
        timeout=timeout
        if timeout is not None
        else settings.utility_timeout_seconds,
        max_retries=max_retries
        if max_retries is not None
        else settings.utility_max_retries,
        tags=["utility_model"],
    )
