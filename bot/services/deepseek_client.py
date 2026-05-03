import asyncio
import logging
from bot.deps import deepseek
from bot.settings import DEEPSEEK_MODEL

log = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 1.5  # seconds


async def chat(messages: list[dict], tools: list[dict] | None = None,
               max_tokens: int = 900, model: str = None) -> dict:
    """DeepSeek API cagrisi — OpenAI-compatible format with retry.

    Args:
        messages: Chat messages
        tools: Tool definitions for function calling
        max_tokens: Max response tokens
        model: Model override (defaults to DEEPSEEK_MODEL from settings)
    """
    kwargs = dict(
        model=model or DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.2,
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
                log.info(f"[deepseek] model={kwargs['model']} tokens: in={usage.prompt_tokens} out={usage.completion_tokens} total={usage.total_tokens}")

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


async def chat_stream(messages: list[dict], model: str = None, max_tokens: int = 900) -> str:
    """DeepSeek streaming API — parça parça üretir, tamamında döndürür.
    Caller her chunk'ı async generator üzerinden okuyabilir."""
    kwargs = dict(
        model=model or DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
        stream=True,
    )
    full_text = []
    try:
        async with await deepseek.chat.completions.create(**kwargs) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    full_text.append(delta)
        return "".join(full_text)
    except Exception as e:
        log.warning(f"[deepseek] stream hatasi, fallback sync: {e}")
        # Streaming başarısız olursa normal çağrıya dön
        resp = await chat(messages, tools=None, model=model, max_tokens=max_tokens)
        return resp["content"] or ""
