import logging
from bot.services.router import classify_intent, get_prefix_routing
from bot.services.orchestrator import orchestrate_search
from bot.services.agent_loop import run_agent

log = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str, send, send_action, context: dict,
                         get_settings, search_cache, get_search_cache_key) -> None:
    """Main message handler: route -> search -> agent -> respond. Optimized v9.2."""
    # Step 0: Extract prefix routing (forced index, cleaned message)
    forced_index, cleaned_text = get_prefix_routing(text)
    if forced_index:
        log.info(f"[handler] prefix route: forced_index={forced_index}")

    # Step 1: Classify intent
    intent = await classify_intent(text)
    log.info(f"[handler] chat={chat_id} intent={intent} forced_index={forced_index} msg={text[:80]}")

    # Get user settings
    settings = get_settings(chat_id)

    # Step 2: Send typing indicator
    await send_action(chat_id, "typing")

    # Step 3: Check cache for identical queries
    cache_key = get_search_cache_key(cleaned_text, intent, forced_index)
    cached = search_cache.get(cache_key)
    if cached:
        log.info(f"[handler] cache hit for: {cache_key[:80]}")
        search_results = cached
    else:
        # Orchestrate search with user settings
        search_results = await orchestrate_search(
            cleaned_text, intent,
            forced_index=forced_index,
            settings=settings,
        )
        # Cache results
        search_cache[cache_key] = search_results

    # Step 4: Run agent loop with search context
    response = await run_agent(cleaned_text, search_results, settings=settings)

    # Step 5: Update conversation history
    history = context.get("history", [])
    history.append({"role": "user", "content": cleaned_text})
    history.append({"role": "assistant", "content": response})
    # Son 20 mesajı tut (10 konuşma turu)
    context["history"] = history[-20:]

    # Step 6: Send response
    await send(chat_id, response)
