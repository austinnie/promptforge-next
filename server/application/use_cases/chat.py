# server/application/use_cases/chat.py
"""对话任务（同步，无需 job 体系）。

因为 chat 通常 1-5 秒，直接同步返回，不走 job + WebSocket。
"""

from engines import dispatcher


async def run_chat(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    engine: str | None = None,
) -> dict:
    text, used_engine = await dispatcher.chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        prefer=engine,
    )
    return {
        "text": text,
        "engine": used_engine,
    }