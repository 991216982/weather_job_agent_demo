from typing import List, Dict, Iterator
from openai import OpenAI


def career_report_stream(client: OpenAI, model: str, system_prompt: str, history: List[Dict[str, str]]) -> Iterator[str]:
    # 将对话历史转换为文本上下文
    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    prompt = (
        f"基于以下的对话历史，为用户生成一份简短的职业规划报告（使用中文）：\n\n"
        f"{context}\n\n"
        "报告内容应包括：\n"
        "1) 总结用户的兴趣、技能与职业目标；\n"
        "2) 基于兴趣与技能的职业方向建议；\n"
        "3) 为实现目标需要学习或提升的关键技能；\n"
        "4) 近 3 个月可实行的行动计划（分步骤）。\n"
    )

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    yield "\n"

