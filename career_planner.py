from typing import Dict, Iterator
from openai import OpenAI


def career_report_stream(client: OpenAI, model: str, system_prompt: str, info: Dict[str, str]) -> Iterator[str]:
    prompt = (
        f"基于以下信息，为用户生成一份简短的职业规划报告（使用中文）：\n"
        f"兴趣：{info.get('interests', '')}\n"
        f"技能：{info.get('skills', '')}\n"
        f"职业目标：{info.get('goals', '')}\n"
        "报告内容应包括：\n"
        "1) 基于兴趣与技能的职业方向建议；\n"
        "2) 为实现目标需要学习或提升的关键技能；\n"
        "3) 近 3 个月可实行的行动计划（分步骤）。\n"
    )

    with client.responses.stream(
        model=model,
        input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
    ) as stream:
        for event in stream:
            if event.type == "response.delta":
                delta = event.delta
                if delta and hasattr(delta, "content") and delta.content:
                    for part in delta.content:
                        if getattr(part, "type", "") == "output_text":
                            yield part.text
            elif event.type == "response.completed":
                yield "\n"
                break

