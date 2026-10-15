import asyncio
import logging

from langchain_core.messages import HumanMessage

from .agent import create_agent
from .chat_ui import (
    ai_label,
    astream_agent_replies,
    error_label,
    hint,
    user_label,
)
from .config import CLI_THREAD_ID, load_settings


def _log_summary_task_done(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except Exception:
        logging.getLogger(__name__).exception("后台摘要更新失败")


async def _run() -> None:
    settings = load_settings()
    if settings.timing_enabled:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(message)s",
        )
    agent = create_agent()

    print(hint("规格定义智能助手已启动。"))
    print(hint("输入 exit、quit 或“退出”可以结束对话。"))

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

        thread_config = {"configurable": {"thread_id": CLI_THREAD_ID}}
        print()
        print(f"{ai_label()}：", end="", flush=True)

        has_output = False
        try:
            async for text in astream_agent_replies(
                agent,
                HumanMessage(content=question),
                thread_config,
            ):
                has_output = True
                print(text, end="", flush=True)
        except Exception as exc:
            has_output = True
            print()
            print(f"{error_label()}：{exc}")

        if not has_output:
            print(hint("（没有收到文本回复）"), end="")
        print()

        summary_task = asyncio.create_task(
            asyncio.to_thread(agent.finalize_memory, thread_config)
        )
        summary_task.add_done_callback(_log_summary_task_done)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
