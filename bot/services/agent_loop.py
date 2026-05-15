import asyncio
import json
import logging
from bot.services.deepseek_client import chat, chat_stream
from bot.tools.search_tools import execute_tool, TOOL_DEFINITIONS
from bot.prompts.system_prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_FAST, SYSTEM_PROMPT_SORU
from bot.settings import MAX_AGENT_ITERATIONS

log = logging.getLogger(__name__)


def _format_context(search_results: dict, max_per_source: int = 5) -> str:
    """Format search results as context for the LLM."""
    parts = []
    if search_results.get("pdfs"):
        parts.append("--- DERS NOTLARI (myppdfs) ---")
        for r in search_results["pdfs"][:max_per_source]:
            if isinstance(r, dict):
                parts.append(r.get("text", ""))
            else:
                parts.append(str(r))
    if search_results.get("brain"):
        parts.append("--- HAFIZA (mybrain) ---")
        for r in search_results["brain"][:max_per_source]:
            if isinstance(r, dict):
                parts.append(r.get("text", ""))
            else:
                parts.append(str(r))
    if search_results.get("questions"):
        parts.append("--- DUS SORULARI ---")
        q_limit = max(3, max_per_source - 2)
        for q in search_results["questions"][:q_limit]:
            parts.append(q.get("question_text", q.get("question", str(q))))
    if search_results.get("anki"):
        parts.append("--- ANKI KARTLARI ---")
        for r in search_results["anki"][:max_per_source]:
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


def _build_history_msg(turn: dict) -> dict:
    """History turn'ü API mesajına dönüştür — reasoning_content varsa koru."""
    msg = {"role": turn["role"], "content": str(turn.get("content", ""))[:2000]}
    rc = turn.get("reasoning_content")
    if rc:
        msg["reasoning_content"] = rc
    return msg


def _build_assistant_msg(resp: dict) -> dict:
    """API yanıtından assistant mesajı oluştur — reasoning_content ve tool_calls dahil."""
    msg: dict = {
        "role": "assistant",
        "content": resp.get("content"),
    }
    if resp.get("reasoning_content"):
        msg["reasoning_content"] = resp["reasoning_content"]
    if resp.get("tool_calls"):
        msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            }
            for tc in resp["tool_calls"]
        ]
    return msg


async def run_agent(
    user_message: str,
    search_results: dict,
    settings: dict | None = None,
    history: list | None = None,
    intent: str | None = None,
    forced_index: str | None = None,
) -> dict:
    """DeepSeek sentez motoru.

    Returns:
        {"content": str, "reasoning_content": str | None}
    """
    if settings is None:
        settings = {}

    speed_mode = settings.get("speed_mode", "balanced")
    model = settings.get("model", "deepseek-v4-pro")
    agent_iterations = settings.get("agent_iterations", 3)
    search_depth = settings.get("search_depth", 5)

    context = _format_context(search_results, max_per_source=search_depth)
    rich = _context_is_rich(search_results)

    if intent == "soru_sor":
        prompt = SYSTEM_PROMPT_SORU
        use_tools = False
        log.info("[agent] soru modu — direkt sentez")
    elif speed_mode == "fast":
        prompt = SYSTEM_PROMPT_FAST
        use_tools = False
    elif forced_index:
        # Exclusive modda (/mypdf, /brain, /anki, /dusbankasi) tool loop atla —
        # kullanıcı zaten hedef index'i seçti, ek arama anlamsız ve webhook timeout'u yapar
        prompt = SYSTEM_PROMPT
        use_tools = False
        log.info(f"[agent] direkt sentez — exclusive mod ({forced_index})")
    elif rich:
        prompt = SYSTEM_PROMPT
        use_tools = False
        log.info(f"[agent] direkt sentez — context zengin")
    else:
        prompt = SYSTEM_PROMPT
        use_tools = True
        log.info("[agent] tool loop — context zayıf")

    messages = [{"role": "system", "content": prompt}]

    # Son 3 konuşma turunu enjekte et (reasoning_content dahil)
    if history:
        for turn in history[-6:]:
            messages.append(_build_history_msg(turn))

    messages.append({
        "role": "user",
        "content": f"KULLANICI MESAJI: {user_message}\n\nONCEDEN GETIRILEN BILGILER:\n{context}",
    })

    # --- Direct Synthesis ---
    if not use_tools:
        if model == "deepseek-reasoner":
            resp = await chat(messages, tools=None, model=model)
            return {
                "content": resp["content"] or "Yanit hazirlanamadi, lutfen tekrar dene.",
                "reasoning_content": resp.get("reasoning_content"),
            }
        else:
            result = await chat_stream(messages, model=model)
            return {
                "content": result["content"] or "Yanit hazirlanamadi, lutfen tekrar dene.",
                "reasoning_content": result.get("reasoning_content"),
            }

    # --- Tool Loop ---
    max_iter = min(agent_iterations, MAX_AGENT_ITERATIONS)
    for iteration in range(max_iter):
        log.info(f"[agent] iterasyon {iteration + 1}/{max_iter} model={model}")
        resp = await chat(messages, tools=TOOL_DEFINITIONS, model=model)

        if resp["tool_calls"]:
            # reasoning_content'i koruyarak assistant mesajını ekle
            messages.append(_build_assistant_msg(resp))

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
            return {
                "content": resp["content"] or "Anladim, yanitinizi hazirliyorum.",
                "reasoning_content": resp.get("reasoning_content"),
            }

    # Loop bitti — final sentez
    log.info("[agent] iterasyon limiti, final sentez")
    try:
        final_resp = await chat(messages, tools=None, model=model)
        return {
            "content": final_resp["content"] or "Arama tamamlandi.",
            "reasoning_content": final_resp.get("reasoning_content"),
        }
    except Exception as e:
        log.error(f"[agent] final sentez hatasi: {e}")
        return {
            "content": "Bilgilere ulastim ancak yanit hazirlanirken hata olustu. Lutfen tekrar dene.",
            "reasoning_content": None,
        }
