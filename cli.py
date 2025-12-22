import sys
from agent import ChatAgent, build_client, get_model_name, stream_text


def main() -> None:
    client = build_client()
    model = get_model_name()
    agent = ChatAgent(client=client, model=model)

    for _chunk in stream_text("你好，我是你的个人助理。你可以试试：\n- 查询北京天气\n- 开始职业规划\n(输入 exit/quit 退出)"):
        sys.stdout.write(_chunk)
        sys.stdout.flush()

    while True:
        try:
            sys.stdout.write("> ")
            sys.stdout.flush()
            user_text = sys.stdin.readline()
            if not user_text:
                break
            user_text = user_text.strip()
            if user_text.lower() in {"exit", "quit"}:
                for _chunk in stream_text("再见，祝你一切顺利！"):
                    sys.stdout.write(_chunk)
                    sys.stdout.flush()
                break
            if not user_text:
                continue
            agent.handle_input(user_text)
        except KeyboardInterrupt:
            for _chunk in stream_text("\n已中断，欢迎下次继续交流。"):
                sys.stdout.write(_chunk)
                sys.stdout.flush()
            break
        except Exception as e:
            for _chunk in stream_text(f"发生错误：{e}"):
                sys.stdout.write(_chunk)
                sys.stdout.flush()


if __name__ == "__main__":
    main()
