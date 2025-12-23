import os
import sys
import time
import random
from typing import List, Dict, Optional

from openai import OpenAI

from weather_service import get_city_weather
from career_planner import career_report_stream


# 系统提示：约束身份与行为
SYSTEM_PROMPT = (
    "你是一位乐于助人的个人助理与信息顾问。\n"
    "- 不承认自己是 AI、语言模型或任何类似实体。\n"
    "- 与用户交流时使用自然、简洁、专业的中文。\n"
    "- 当用户询问天气时，响应应包含城市、温度与天气描述。\n"
    "- 始终以流式方式输出。\n"
)

# 职业规划专用提示词
CAREER_SYSTEM_PROMPT = (
    "你是一位专业的职业规划师。你的目标是通过自然的对话收集用户的【兴趣】、【技能】和【职业目标】。\n"
    "- 不要像填表一样机械提问，要根据用户的回答进行追问或引导，一次只问一个主要问题。\n"
    "- 保持亲切、专业的语气。\n"
    "- 当你认为已经收集到足够的信息（兴趣、技能、目标都清晰）后，请总结一下并询问用户是否现在生成报告。\n"
    "- 如果用户明确表示同意（例如“好的”、“可以”、“生成吧”），请**仅**回复 `[GENERATE_REPORT]`，不要包含其他任何文字。\n"
)


def stream_text(text: str, base_delay: float = 0.01, end: str = "\n"):
    """将纯文本以流式方式输出到终端，模拟打字机效果。"""
    for char in text:
        yield char
        # 加入微小的随机延迟，模拟自然打字感
        time.sleep(base_delay + random.uniform(0, 0.02))
    yield end


def print_stream(data, end: str = "\n"):
    """
    统一输出流式数据或静态文本。
    - 如果 data 是字符串：调用 stream_text 模拟流式输出（带打字机效果）。
    - 如果 data 是迭代器：直接输出（通常是 LLM 的实时响应）。
    """
    if isinstance(data, str):
        iterator = stream_text(data, end=end)
    else:
        iterator = data
        
    for part in iterator:
        sys.stdout.write(part)
        sys.stdout.flush()


def stream_llm_reply(client: OpenAI, model: str, system_prompt: str, user_text: str):
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    yield "\n"


class ChatAgent:
    """一个具备天气查询与职业规划报告功能的简单聊天代理。"""

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
        self.in_career_mode: bool = False
        self.career_history: List[Dict[str, str]] = []

    # ======= 职业规划流程 =======
    def start_career_flow(self) -> None:
        self.in_career_mode = True
        self.career_history = []
        # 由 AI 发起第一句问候
        initial_user_input = "你好，我想做职业规划。"
        self.handle_career_flow(initial_user_input, is_hidden_input=True)

    def handle_career_flow(self, user_text: str, is_hidden_input: bool = False) -> None:
        # 将用户输入加入历史（如果是隐藏输入，则不打印，但加入历史作为触发）
        # 这里稍微特殊处理：如果是用户真的输入了，才加 User role。
        # 如果是 hidden input (触发语)，我们也加进去，当作用户说的。
        self.career_history.append({"role": "user", "content": user_text})

        # 构建完整的消息列表：System + History
        messages = [{"role": "system", "content": CAREER_SYSTEM_PROMPT}] + self.career_history

        # 调用 LLM
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )

        full_reply = ""
        # 实时流式输出
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_reply += content
                # 如果是特殊指令，暂时不输出到屏幕（或者输出也没关系，因为很短）
                if "[GENERATE_REPORT]" not in full_reply:
                    sys.stdout.write(content)
                    sys.stdout.flush()
        
        # 换行
        if "[GENERATE_REPORT]" not in full_reply:
             sys.stdout.write("\n")

        # 检查是否触发报告生成
        if "[GENERATE_REPORT]" in full_reply:
            print_stream("\n正在为您生成职业规划报告，请稍候...\n")
            self.generate_career_report()
            return

        # 将 AI 回复加入历史
        self.career_history.append({"role": "assistant", "content": full_reply})

    def generate_career_report(self) -> None:
        # 使用 career_planner.py 中的函数，传入完整的对话历史
        for chunk in career_report_stream(
            client=self.client,
            model=self.model,
            system_prompt=SYSTEM_PROMPT, # 报告生成可以用通用的助手身份，或者保持专业
            history=self.career_history,
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        
        # 结束流程
        self.in_career_mode = False
        print_stream("\n报告生成完毕。职业规划流程结束。")

    # ======= 天气查询 =======
    def handle_weather_query(self, user_text: str) -> bool:
        """简单识别并处理天气查询。返回 True 表示已处理。"""
        lowered = user_text.strip().lower()
        if ("天气" in user_text) or ("weather" in lowered):
            # 尝试抽取城市名：匹配“X天气”或“查询X天气”等形式
            city = extract_city_name(user_text)
            if not city:
                print_stream("请告诉我要查询的城市名称，例如：上海天气。")
                return True
            info = get_city_weather(city)
            if not info:
                print_stream("抱歉，我暂时无法获取该城市的实时天气，请稍后再试。")
                return True
            # 以流式方式输出结果
            text = (
                f"{info['city']} 当前天气：\n"
                f"- 温度：{info['temperature_c']}℃\n"
                f"- 天气：{info['description']}\n"
                f"- 观测时间：{info['observed_at']}\n"
            )
            print_stream(text)
            return True
        return False

    # ======= 通用处理 =======
    def handle_input(self, user_text: str) -> None:
        # 退出职业规划流程
        if user_text.strip() in {"退出", "取消", "停止"} and self.in_career_mode:
            self.in_career_mode = False
            self.career_history = []
            print_stream("好的，已退出职业规划流程。如果需要，随时可以重新开始。")
            return

        # 如果正在进行职业规划问答
        if self.in_career_mode:
            self.handle_career_flow(user_text)
            return

        # 触发职业规划流程
        if any(keyword in user_text for keyword in ["职业规划", "职业建议", "规划报告"]):
            self.start_career_flow()
            return

        # 天气查询
        if self.handle_weather_query(user_text):
            return

        # 其他情况：交给模型进行通用回复（流式）
        print_stream(stream_llm_reply(self.client, self.model, SYSTEM_PROMPT, user_text))


def extract_city_name(text: str) -> Optional[str]:
    """极简城市名抽取：优先匹配“XX天气”、“查询XX天气”。"""
    s = text.strip()
    # 处理中文常见表达
    for marker in ["查询", "看看", "了解", "查看"]:
        if s.endswith("天气") and marker in s:
            # 例如：查询北京天气 => 去掉“查询”和“天气”
            s2 = s.replace(marker, "")
            s2 = s2.replace("天气", "")
            return s2.strip() or None
    if s.endswith("天气"):
        return s[:-2].strip() or None
    # 英文：weather in X
    lowered = s.lower()
    if "weather in" in lowered:
        return lowered.split("weather in", 1)[1].strip() or None
    return None


def build_client() -> OpenAI:
    """构建 OpenAI 客户端，优先使用 DASHSCOPE_API_KEY (阿里云百炼)，其次 OPENAI_API_KEY。"""
    # 默认使用阿里云百炼兼容端点
    default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 优先检查阿里云百炼 Key
    aliyun_key = os.getenv("DASHSCOPE_API_KEY", "")

    api_key = aliyun_key
    # 如果未显式设置 BASE_URL，则自动使用阿里云端点
    base_url = os.getenv("OPENAI_BASE_URL", default_base_url)

    if not api_key:
        print_stream("警告：未检测到 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，职业规划报告将不可用。")
        
    return OpenAI(base_url=base_url, api_key=api_key)


def get_model_name() -> str:
    """读取模型名称，默认使用 qwen-plus (阿里云)。"""
    return os.getenv("OPENAI_MODEL", "qwen3-max")
