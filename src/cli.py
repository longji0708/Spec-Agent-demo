from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from .agent import create_agent
from .chat_ui import ai_label, error_label, hint, stream_agent_replies, user_label
from .config import CLI_THREAD_ID


def main() -> None:
    load_dotenv()
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
            for text in stream_agent_replies(
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


if __name__ == "__main__":
    main()
