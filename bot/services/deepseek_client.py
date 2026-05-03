import asyncio
import logging
from bot.deps import deepseek
from bot.settings import DEEPSEEK_MODEL

log = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 1.5  # seconds


async def chat(messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 4096) -> dict:
    """DeepSeek V4 Pro API cagrisi — OpenAI-compatible format with retry."""
    kwargs = dict(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=max_tokens,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
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
                "finish_reason": resp.choices[0].finish_reason,
            }
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * (attempt + 1)
                log.warning(f"[deepseek] attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                log.error(f"[deepseek] all {MAX_RETRIES + 1} attempts failed: {e}")

    raise last_error
