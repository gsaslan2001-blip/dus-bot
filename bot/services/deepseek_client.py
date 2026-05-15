import asyncio
import json
import logging
import re
import uuid
from bot.deps import deepseek
from bot.settings import DEEPSEEK_MODEL

log = logging.getLogger(__name__)

# DeepSeek thinking mode sometimes emits tool calls as DSML in msg.content
_DSML_INVOKE_RE = re.compile(
    r'<｜｜DSML｜｜invoke name="([^"]+)">(.*?)</｜｜DSML｜｜invoke>',
    re.DOTALL,
)
_DSML_PARAM_RE = re.compile(
    r'<｜｜DSML｜｜parameter name="([^"]+)"[^>]*>(.*?)</｜｜DSML｜｜parameter>',
    re.DOTALL,
)


def _parse_dsml_tool_calls(content: str) -> list[dict]:
    """DSML-formatted tool calls'ı standart OpenAI formatına dönüştür."""
    calls = []
    for m in _DSML_INVOKE_RE.finditer(content):
        tool_name = m.group(1)
        args = {
            pm.group(1): pm.group(2).strip()
            for pm in _DSML_PARAM_RE.finditer(m.group(2))
        }
        calls.append({
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "name": tool_name,
            "arguments": json.dumps(args, ensure_ascii=False),
        })
    return calls

MAX_RETRIES = 2
RETRY_DELAY = 1.5  # seconds


async def chat(messages: list[dict], tools: list[dict] | None = None,
               max_tokens: int = 1400, model: str = None) -> dict:
    """DeepSeek API çağrısı — OpenAI-compatible format, retry destekli.

    Returns dict:
        content          : str | None  — model yanıtı
        reasoning_content: str | None  — thinking mode zinciri (varsa)
        tool_calls       : list        — function call listesi
        finish_reason    : str | None
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
                log.info(
                    f"[deepseek] model={kwargs['model']} "
                    f"tokens: in={usage.prompt_tokens} out={usage.completion_tokens}"
                )

            # thinking mode: reasoning_content alanını koru
            reasoning_content = getattr(msg, "reasoning_content", None)

            tool_calls_list = [
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                for tc in (msg.tool_calls or [])
            ]

            content = msg.content
            # Thinking mode fallback: tool calls gömülü DSML XML olarak content'te gelebilir
            if not tool_calls_list and content and "<｜｜DSML｜｜tool_calls>" in content:
                tool_calls_list = _parse_dsml_tool_calls(content)
                if tool_calls_list:
                    log.info(f"[deepseek] DSML fallback: {len(tool_calls_list)} tool call content'ten parse edildi")
                    content = None  # DSML text yanıt değil, temizle

            return {
                "content": content,
                "reasoning_content": reasoning_content,
                "tool_calls": tool_calls_list,
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


async def chat_stream(messages: list[dict], model: str = None, max_tokens: int = 1400) -> dict:
    """DeepSeek streaming API — content + reasoning_content döner.

    Returns dict:
        content          : str  — model yanıtı
        reasoning_content: str | None  — thinking zinciri (stream'den toplandı)
    """
    kwargs = dict(
        model=model or DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
        stream=True,
    )
    full_content = []
    full_reasoning = []
    try:
        stream = await deepseek.chat.completions.create(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                full_content.append(delta.content)
            rc = getattr(delta, "reasoning_content", None)
            if rc:
                full_reasoning.append(rc)
        return {
            "content": "".join(full_content),
            "reasoning_content": "".join(full_reasoning) or None,
        }
    except Exception as e:
        log.warning(f"[deepseek] stream hatasi, fallback sync: {e}")
        resp = await chat(messages, tools=None, model=model, max_tokens=max_tokens)
        return {
            "content": resp["content"] or "",
            "reasoning_content": resp.get("reasoning_content"),
        }
