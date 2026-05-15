import asyncio
import json
import logging
from bot.services.deepseek_client import chat, chat_stream
from bot.tools.search_tools import execute_tool, TOOL_DEFINITIONS
from bot.prompts.system_prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_FAST, SYSTEM_PROMPT_SORU
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


def _context_is_rich(search_results: dict) -> bool:
    """Orchestrator'dan gelen sonuçlar yeterliyse True — tool loop atlanır."""
    total = (
        len(search_results.get("pdfs", [])) +
        len(search_results.get("brain", [])) +
        len(search_results.get("questions", [])) +
        len(search_results.get("anki", []))
    )
    return total >= 3


async def run_agent(user_message: str, search_results: dict, settings: dict | None = None, history: list | None = None, intent: str | None = None) -> str:
    """DeepSeek sentez motoru. Context doluysa tool loop atlanır (Direct Synthesis)."""
    if settings is None:
        settings = {}

    speed_mode = settings.get("speed_mode", "balanced")
    model = settings.get("model", "deepseek-v4-pro")
    agent_iterations = settings.get("agent_iterations", 3)

    context = _format_context(search_results)
    rich = _context_is_rich(search_results)

    # Intent-specific prompts
    if intent == "soru_sor":
        prompt = SYSTEM_PROMPT_SORU
        use_tools = False  # Soru modu: direkt sentez (sadece 5 soru)
        log.info(f"[agent] soru modu — 5 soru output")
    elif speed_mode == "fast":
        prompt = SYSTEM_PROMPT_FAST
        use_tools = False  # Fast: her zaman direkt sentez
    elif rich:
        prompt = SYSTEM_PROMPT
        use_tools = False  # Dengeli/Kapsamlı ama context zaten dolu: direkt sentez
        log.info(f"[agent] direct synthesis — context rich ({sum(len(v) for v in search_results.values() if isinstance(v, list))} sonuc)")
    else:
        prompt = SYSTEM_PROMPT
        use_tools = True   # Context boş: tool loop devreye girer
        log.info(f"[agent] tool loop — context zayif")

    messages = [{"role": "system", "content": prompt}]

    # Son 3 konuşma turunu inject et
    if history:
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": str(turn["content"])[:2000]})

    messages.append(
        {"role": "user", "content": f"KULLANICI MESAJI: {user_message}\n\nONCEDEN GETIRILEN BILGILER:\n{context}"}
    )

    # --- Direct Synthesis (tool loop yok) ---
    # Reasoner modeli streaming'i desteklemeyebilir, sync chat kullan
    if not use_tools:
        if model == "deepseek-reasoner":
            resp = await chat(messages, tools=None, model=model)
            return resp["content"] or "Yanit hazirlanamadi, lutfen tekrar dene."
        else:
            result = await chat_stream(messages, model=model)
            return result or "Yanit hazirlanamadi, lutfen tekrar dene."

    # --- Tool Loop (context zayıf olduğunda) ---
    max_iter = min(agent_iterations, MAX_AGENT_ITERATIONS)
    for iteration in range(max_iter):
        log.info(f"[agent] iterasyon {iteration + 1}/{max_iter} model={model}")
        resp = await chat(messages, tools=TOOL_DEFINITIONS, model=model)

        if resp["tool_calls"]:
            messages.append({
                "role": "assistant",
                "content": resp["content"],
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in resp["tool_calls"]
                ]
            })
            # Paralel tool execution
            async def _exec(tc):
                try:
                    return tc["id"], await execute_tool(tc["name"], json.loads(tc["arguments"]))
                except Exception as e:
                    return tc["id"], f"Tool hatasi: {e}"

            results = await asyncio.gather(*[_exec(tc) for tc in resp["tool_calls"]])
            for tc_id, result in results:
                messages.append({"role": "tool", "tool_call_id": tc_id, "content": str(result)[:8000]})
        else:
            return resp["content"] or "Anladim, yanitinizi hazirliyorum."

    # Loop bitti — final sentez
    log.info("[agent] iterasyon limiti, final sentez")
    try:
        final_resp = await chat(messages, tools=None, model=model)
        return final_resp["content"] or "Arama tamamlandi."
    except Exception as e:
        log.error(f"[agent] final sentez hatasi: {e}")
        return "Bilgilere ulastim ancak yanit hazirlanirken hata olustu. Lutfen tekrar dene."
