import logging
from bot.services.router import classify_intent, get_prefix_routing
from bot.services.orchestrator import orchestrate_search
from bot.services.agent_loop import run_agent

log = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str, send, send_action, context: dict) -> None:
    """Main message handler: route -> search -> agent -> respond."""
    # Step 0: Extract prefix routing (forced index, cleaned message)
    forced_index, cleaned_text = get_prefix_routing(text)
    if forced_index:
        log.info(f"[handler] prefix route: forced_index={forced_index}")

    # Step 1: Classify intent
    intent = await classify_intent(text)
    log.info(f"[handler] chat={chat_id} intent={intent} forced_index={forced_index} msg={text[:80]}")

    # Step 2: Send typing indicator
    await send_action(chat_id, "typing")

    # Step 3: Orchestrate search across indexes
    search_results = await orchestrate_search(cleaned_text, intent, forced_index=forced_index)

    # Step 4: Run agent loop with search context (use original text for agent)
    response = await run_agent(cleaned_text, search_results)

    # Step 5: Send response (chunked for Telegram's 4096 limit)
    await send(chat_id, response)
