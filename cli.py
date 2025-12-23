import sys
import traceback

from agent import ChatAgent, build_client, get_model_name, print_stream


def main() -> None:
    client = build_client()
    model = get_model_name()
    agent = ChatAgent(client=client, model=model)

    print_stream("你好，我是你的个人助理。你可以试试：\n- 查询北京天气\n- 开始职业规划\n(输入 exit/quit 退出)")

    while True:
        try:
            print_stream("> ", end="")
            user_text = sys.stdin.readline()
            if not user_text:
                break
            user_text = user_text.strip()
            if user_text.lower() in {"exit", "quit"}:
                print_stream("再见，祝你一切顺利！")
                break
            if not user_text:
                continue
            agent.handle_input(user_text)
        except KeyboardInterrupt:
            print_stream("\n已中断，欢迎下次继续交流。")
            break
        except Exception as e:
            print(traceback.format_exc())
            print_stream(f"发生错误：{e}")


if __name__ == "__main__":
    main()
