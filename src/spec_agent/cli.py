import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from .agent import create_agent
from .chat_ui import (
    ai_label,
    astream_agent_replies,
    error_label,
    hint,
    stream_agent_replies,
    user_label,
)
from .config import CLI_THREAD_ID, load_settings
from .demo import create_demo_models


def _log_summary_task_done(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except Exception:
        logging.getLogger(__name__).exception("后台摘要更新失败")


def _thread_config() -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": CLI_THREAD_ID}}


async def _run_once(
    agent: Any,
    question: str,
    *,
    demo: bool,
) -> None:
    print()
    print(f"{ai_label()}：", end="", flush=True)

    has_output = False
    try:
        if demo:
            for text in stream_agent_replies(
                agent,
                HumanMessage(content=question),
                _thread_config(),
            ):
                has_output = True
                print(text, end="", flush=True)
        else:
            async for text in astream_agent_replies(
                agent,
                HumanMessage(content=question),
                _thread_config(),
            ):
                if not getattr(text, "is_progress", False):
                    has_output = True
                print(text, end="", flush=True)
    except Exception as exc:
        has_output = True
        print()
        print(f"{error_label()}：{exc}")

    if not has_output:
        print(hint("（没有收到文本回复）"), end="")
    print()


async def _run(
    *,
    prompt: str | None,
    demo: bool,
    storage_path: Path | None,
    project_id: str,
) -> None:
    settings = load_settings()
    if settings.timing_enabled:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(message)s",
        )

    if demo:
        chat_model, utility_model = create_demo_models()
        agent = create_agent(
            chat_model=chat_model,
            utility_model=utility_model,
            storage_path=storage_path,
            project_id=project_id,
        )
        print(hint("演示模式已启动，不需要真实 API Key。"))
    else:
        agent = create_agent(
            storage_path=storage_path,
            project_id=project_id,
        )
        print(hint("规格定义智能助手已启动。"))

    print(hint("输入 exit、quit 或“退出”可以结束对话。"))

    if prompt is not None:
        await _run_once(agent, prompt, demo=demo)
        return

    while True:
        try:
            question = input(f"\n{user_label()}：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit", "退出"}:
            break

        await _run_once(agent, question, demo=demo)
        summary_task = asyncio.create_task(
            asyncio.to_thread(agent.finalize_memory, _thread_config())
        )
        summary_task.add_done_callback(_log_summary_task_done)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="AI 项目规格定义器")
    parser.add_argument("--prompt", help="非交互模式：只处理一条输入后退出")
    parser.add_argument("--demo", action="store_true", help="使用本地 Fake LLM，无需 API Key")
    parser.add_argument("--storage", type=Path, help="规格 JSON 持久化文件路径")
    parser.add_argument("--project", default="default", help="项目 ID，默认 default")
    args = parser.parse_args(argv)
    try:
        asyncio.run(
            _run(
                prompt=args.prompt,
                demo=args.demo,
                storage_path=args.storage,
                project_id=args.project,
            )
        )
    except ValueError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
