import logging
from bot.deps import deepseek
from bot.settings import DEEPSEEK_MODEL

log = logging.getLogger(__name__)


async def chat(messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 4096) -> dict:
    """DeepSeek V4 Pro API cagrisi — OpenAI-compatible format."""
    kwargs = dict(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=max_tokens,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    resp = await deepseek.chat.completions.create(**kwargs)
    msg = resp.choices[0].message

    usage = resp.usage
    if usage:
        log.info(f"[deepseek] tokens: in={usage.prompt_tokens} out={usage.completion_tokens} total={usage.total_tokens}")

    return {
        "content": msg.content,
        "tool_calls": [
            {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
            for tc in (msg.tool_calls or [])
        ],
        "finish_reason": msg.finish_reason or resp.choices[0].finish_reason,
    }
