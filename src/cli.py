from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from .agent import create_deepseek_agent
from .config import CLI_THREAD_ID


def main() -> None:
    load_dotenv()
    agent = create_deepseek_agent()

    print("DeepSeek 智能体已启动，输入 exit 或 quit 退出。")
    while True:
        try:
            question = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit", "退出"}:
            break

        thread_config = {"configurable": {"thread_id": CLI_THREAD_ID}}
        result = agent.invoke(
            {"messages": [HumanMessage(content=question)]},
            config=thread_config,
        )
        answer = result["messages"][-1].content
        print("智能体：", answer)


if __name__ == "__main__":
    main()
