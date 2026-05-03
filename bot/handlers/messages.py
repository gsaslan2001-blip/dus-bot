import logging
from bot.services.router import classify_intent, get_prefix_routing
from bot.services.orchestrator import orchestrate_search
from bot.services.agent_loop import run_agent

log = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str, send, send_action, context: dict,
                         get_settings, search_cache, get_search_cache_key,
                         send_placeholder=None, edit_message=None) -> None:
    """Main message handler: route -> search -> agent -> respond."""
    # Step 0: Prefix routing
    forced_index, cleaned_text = get_prefix_routing(text)
    if forced_index:
        log.info(f"[handler] prefix route: forced_index={forced_index}")

    # Step 1: Intent
    intent = await classify_intent(text)
    log.info(f"[handler] chat={chat_id} intent={intent} forced_index={forced_index} msg={text[:80]}")

    settings = get_settings(chat_id)

    # Step 2: Placeholder mesajı gönder (kullanıcı hemen bir şey görür)
    placeholder_msg_id = None
    if send_placeholder:
        placeholder_msg_id = await send_placeholder(chat_id)
    else:
        await send_action(chat_id, "typing")

    # Step 3: Cache kontrolü
    cache_key = get_search_cache_key(cleaned_text, intent, forced_index)
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

    # Step 4: Agent
    prior_history = context.get("history", [])
    response = await run_agent(cleaned_text, search_results, settings=settings, history=prior_history)

    # Step 5: Geçmişi güncelle
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
