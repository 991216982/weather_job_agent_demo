import os
import sys
from typing import Dict, Optional

from openai import OpenAI

from weather_service import get_city_weather
from career_planner import career_report_stream


# 系统提示：约束身份与行为（不透露模型身份，作为个人助理）
SYSTEM_PROMPT = (
    "你是一位乐于助人的个人助理与信息顾问。\n"
    "- 不承认自己是 AI、语言模型或任何类似实体。\n"
    "- 与用户交流时使用自然、简洁、专业的中文。\n"
    "- 当用户请求职业规划建议时，先通过提问收集兴趣、技能与职业目标，再生成报告。\n"
    "- 当用户询问天气时，响应应包含城市、温度与天气描述。\n"
    "- 始终以流式方式输出。\n"
)


def stream_text(text: str, chunk: int = 8):
    """将纯文本以流式方式输出到终端。"""
    for i in range(0, len(text), chunk):
        yield text[i : i + chunk]
    yield "\n"


class ChatAgent:
    """一个具备天气查询与职业规划报告功能的简单聊天代理。"""

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
        self.state: str = "idle"
        self.career_info: Dict[str, str] = {}

    # ======= 职业规划流程 =======
    def start_career_flow(self) -> None:
        self.state = "career_interest"
        self.career_info = {}
        for _chunk in stream_text("好的，我们先来做一个简短的职业规划。请告诉我你的兴趣方向（例如：数据、设计、金融、教育等）。"):
            sys.stdout.write(_chunk)
            sys.stdout.flush()

    def handle_career_flow(self, user_text: str) -> None:
        if self.state == "career_interest":
            self.career_info["interests"] = user_text.strip()
            self.state = "career_skills"
            for _chunk in stream_text("了解了。接下来，请简要说明你目前具备的技能或学习过的方向（例如：Python、SQL、市场分析、沟通协作等）。"):
                sys.stdout.write(_chunk)
                sys.stdout.flush()
            return

        if self.state == "career_skills":
            self.career_info["skills"] = user_text.strip()
            self.state = "career_goals"
            for _chunk in stream_text("很好。最后，请告诉我你的职业目标（例如：数据分析师、产品经理、设计师，或你希望的行业/岗位）。"):
                sys.stdout.write(_chunk)
                sys.stdout.flush()
            return

        if self.state == "career_goals":
            self.career_info["goals"] = user_text.strip()
            self.state = "career_ready"
            self.generate_career_report()
            self.state = "idle"

    def generate_career_report(self) -> None:
        for chunk in career_report_stream(
            client=self.client,
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            info=self.career_info,
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()

    # ======= 天气查询 =======
    def handle_weather_query(self, user_text: str) -> bool:
        """简单识别并处理天气查询。返回 True 表示已处理。"""
        lowered = user_text.strip().lower()
        if ("天气" in user_text) or ("weather" in lowered):
            # 尝试抽取城市名：匹配“X天气”或“查询X天气”等形式
            city = extract_city_name(user_text)
            if not city:
                for _chunk in stream_text("请告诉我要查询的城市名称，例如：上海天气。"):
                    sys.stdout.write(_chunk)
                    sys.stdout.flush()
                return True
            info = get_city_weather(city)
            if not info:
                for _chunk in stream_text("抱歉，我暂时无法获取该城市的实时天气，请稍后再试。"):
                    sys.stdout.write(_chunk)
                    sys.stdout.flush()
                return True
            # 以流式方式输出结果
            text = (
                f"{info['city']} 当前天气：\n"
                f"- 温度：{info['temperature_c']}℃\n"
                f"- 天气：{info['description']}\n"
                f"- 观测时间：{info['observed_at']}\n"
            )
            for _chunk in stream_text(text):
                sys.stdout.write(_chunk)
                sys.stdout.flush()
            return True
        return False

    # ======= 通用处理 =======
    def handle_input(self, user_text: str) -> None:
        # 退出职业规划流程
        if user_text.strip() in {"退出", "取消", "停止"} and self.state.startswith("career"):
            self.state = "idle"
            for _chunk in stream_text("好的，已退出职业规划流程。如果需要，随时可以重新开始。"):
                sys.stdout.write(_chunk)
                sys.stdout.flush()
            return

        # 如果正在进行职业规划问答
        if self.state.startswith("career") and self.state != "idle":
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
        with self.client.responses.stream(
            model=self.model,
            input=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}],
        ) as stream:
            for event in stream:
                if event.type == "response.delta":
                    delta = event.delta
                    if delta and hasattr(delta, "content") and delta.content:
                        for part in delta.content:
                            if getattr(part, "type", "") == "output_text":
                                sys.stdout.write(part.text)
                                sys.stdout.flush()
                elif event.type == "response.completed":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break


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
    """构建 OpenAI 客户端，支持自定义 base_url 与 API key。"""
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        for _chunk in stream_text("警告：未检测到 OPENAI_API_KEY，职业规划报告将不可用。请在运行前设置环境变量。"):
            sys.stdout.write(_chunk)
            sys.stdout.flush()
    return OpenAI(base_url=base_url, api_key=api_key)


def get_model_name() -> str:
    """读取模型名称，默认使用一个支持 Responses API 的模型。"""
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
