import json
import logging
from bot.services.deepseek_client import chat
from bot.tools.search_tools import execute_tool, TOOL_DEFINITIONS
from bot.prompts.system_prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_FAST
from bot.settings import MAX_AGENT_ITERATIONS

log = logging.getLogger(__name__)


def _format_context(search_results: dict) -> str:
    """Format search results as context for the LLM."""
    parts = []
    if search_results.get("pdfs"):
        parts.append("--- DERS NOTLARI (myppdfs) ---")
        for r in search_results["pdfs"][:5]:
            if isinstance(r, dict):
                parts.append(r.get("text", ""))
            else:
                parts.append(str(r))
    if search_results.get("brain"):
        parts.append("--- HAFIZA (mybrain) ---")
        for r in search_results["brain"][:5]:
            if isinstance(r, dict):
                parts.append(r.get("text", ""))
            else:
                parts.append(str(r))
    if search_results.get("questions"):
        parts.append("--- DUS SORULARI ---")
        for q in search_results["questions"][:3]:
            parts.append(q.get("question_text", q.get("question", str(q))))
    if search_results.get("anki"):
        parts.append("--- ANKI KARTLARI ---")
        for r in search_results["anki"][:3]:
            if isinstance(r, dict):
                parts.append(r.get("text", ""))
            else:
                parts.append(str(r))
    return "\n\n".join(parts)


async def run_agent(user_message: str, search_results: dict, settings: dict | None = None, history: list | None = None) -> str:
    """DeepSeek function-calling agent loop. Optimized for speed in fast mode."""
    if settings is None:
        settings = {}

    speed_mode = settings.get("speed_mode", "balanced")
    model = settings.get("model", "deepseek-chat")
    agent_iterations = settings.get("agent_iterations", 3)

    context = _format_context(search_results)

    # Fast mode: Use simplified prompt, skip agent loop entirely
    if speed_mode == "fast":
        prompt = SYSTEM_PROMPT_FAST
        max_iter = 1
    else:
        prompt = SYSTEM_PROMPT
        max_iter = min(agent_iterations, MAX_AGENT_ITERATIONS)

    messages = [
        {"role": "system", "content": prompt},
    ]

    # Son 3 konuşma turunu (6 mesaj) inject et
    if history:
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": str(turn["content"])[:2000]})

    messages.append(
        {"role": "user", "content": f"KULLANICI MESAJI: {user_message}\n\nONCEDEN GETIRILEN BILGILER:\n{context}"}
    )

    for iteration in range(max_iter):
        log.info(f"[agent] iterasyon {iteration + 1}/{max_iter} model={model}")
        resp = await chat(messages, tools=TOOL_DEFINITIONS, model=model)

        if resp["tool_calls"]:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": resp["content"],
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in resp["tool_calls"]
                ]
            })
            # Execute each tool and add results
            for tc in resp["tool_calls"]:
                try:
                    args = json.loads(tc["arguments"])
                    result = await execute_tool(tc["name"], args)
                except Exception as e:
                    result = f"Tool hatasi: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result[:8000]
                })
        else:
            return resp["content"] or "Anladim, yanitinizi hazirliyorum."

    # Loop bitti ama hala tool call'lar vardı — toplanan bilgilerden final sentez yap
    log.info(f"[agent] iterasyon limiti doldu, final sentez cagirisi yapiliyor")
    try:
        final_resp = await chat(messages, tools=None, model=model)
        return final_resp["content"] or "Arama tamamlandi, bilgiler yuklendi."
    except Exception as e:
        log.error(f"[agent] final sentez hatasi: {e}")
        return "Gerekli bilgilere ulastim ancak yanit hazirlanirken hata olustu. Lutfen tekrar dene."
