import asyncio
import logging
from datetime import datetime
from pathlib import Path
from bot.services.router import route_message, get_prefix_help, classify_intent
from bot.services.orchestrator import orchestrate_search
from bot.services.agent_loop import run_agent

VEKTORLENECEK = Path(__file__).parent.parent.parent / "vektörlenecek"

async def _persist_chat_turn(chat_id: int, intent: str, user_text: str, assistant_text: str) -> None:
    try:
        VEKTORLENECEK.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = VEKTORLENECEK / f"chat_{chat_id}_{ts}.md"
        content = (
            f"# Chat Turn — {ts}\n\n"
            f"**intent:** {intent}\n\n"
            f"**user:** {user_text}\n\n"
            f"**assistant:** {assistant_text}\n"
        )
        filepath.write_text(content, encoding="utf-8")
    except Exception as e:
        logging.getLogger(__name__).warning(f"[chathistory] persist başarısız: {e}")

log = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str, send, send_action, context: dict,
                         get_settings, search_cache, get_search_cache_key,
                         send_placeholder=None, edit_message=None) -> None:
    """Ana mesaj işleyici: route → search → agent → respond."""

    # Step 0: Tek geçişte yönlendirme
    intent_override, forced_index, cleaned_text, is_prefix_only = route_message(text)

    # Prefix tek başına gönderildi → arama yapma, yardım mesajı göster
    if is_prefix_only:
        await send(chat_id, get_prefix_help(forced_index), parse_mode="")
        return

    # Step 1: Intent — prefix belirlediyse DeepSeek çağrısını atla
    if intent_override:
        intent = intent_override
        log.info(f"[handler] prefix route: intent={intent} forced={forced_index} msg={cleaned_text[:80]}")
    else:
        intent = await classify_intent(cleaned_text)
        log.info(f"[handler] classified: intent={intent} msg={cleaned_text[:80]}")

    settings = get_settings(chat_id)

    # Step 2: Placeholder gönder (kullanıcı hemen bir şey görür)
    placeholder_msg_id = None
    if send_placeholder:
        placeholder_msg_id = await send_placeholder(chat_id)
    else:
        await send_action(chat_id, "typing")

    # Step 3: Cache kontrolü
    cache_key = get_search_cache_key(cleaned_text, intent, forced_index, settings)
    cached = search_cache.get(cache_key)
    if cached:
        log.info(f"[handler] cache hit: {cache_key[:80]}")
        search_results = cached
    else:
        search_results = await orchestrate_search(
            cleaned_text, intent,
            forced_index=forced_index,
            settings=settings,
        )
        search_cache[cache_key] = search_results

    # Step 4: Response generation
    prior_history = context.get("history", [])

    # /soru intent: Format Pinecone questions directly (no agent synthesis)
    if intent == "soru_sor":
        questions = search_results.get("questions", [])
        if not questions:
            response = "Pinecone soru bankasında bu sorgu için uygun soru bulunamadi."
        else:
            # Format max 5 questions from Pinecone dusbankasi
            lines = []
            for i, q in enumerate(questions[:5], 1):
                lines.append(f"**SORU {i}:**\n{q.get('question', '')}\n")
                lines.append(f"A) {q.get('option_a', '')}")
                lines.append(f"B) {q.get('option_b', '')}")
                lines.append(f"C) {q.get('option_c', '')}")
                lines.append(f"D) {q.get('option_d', '')}")
                lines.append(f"E) {q.get('option_e', '')}\n")
                lines.append(f"**Cevap:** {q.get('correct_answer', '')}")
                lines.append(f"**Açıklama:** {q.get('explanation', '')}\n")
            response = "\n".join(lines)
    else:
        # Other intents: Use agent synthesis
        response = await run_agent(cleaned_text, search_results, settings=settings, history=prior_history, intent=intent)

    # Step 5: Konuşma geçmişini güncelle
    history = context.get("history", [])
    history.append({"role": "user", "content": cleaned_text})
    history.append({"role": "assistant", "content": response})
    context["history"] = history[-20:]

    # Step 6: Yanıtı gönder — placeholder varsa edit, yoksa yeni mesaj
    if placeholder_msg_id and edit_message and len(response) <= 4000:
        ok = await edit_message(chat_id, placeholder_msg_id, response)
        if not ok:
            await send(chat_id, response, parse_mode="")
    else:
        await send(chat_id, response, parse_mode="")

    # Step 7: chathistory staging (non-blocking)
    asyncio.create_task(_persist_chat_turn(chat_id, intent, cleaned_text, response))
