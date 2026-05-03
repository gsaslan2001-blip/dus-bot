import logging
from bot.services.router import classify_intent
from bot.services.orchestrator import orchestrate_search
from bot.services.agent_loop import run_agent

log = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str, send, send_action, context: dict) -> None:
    """Main message handler: route -> search -> agent -> respond."""
    # Step 1: Classify intent
    intent = await classify_intent(text)
    log.info(f"[handler] chat={chat_id} intent={intent} msg={text[:80]}")

    # Step 2: Send typing indicator
    await send_action(chat_id, "typing")

    # Step 3: Orchestrate search across indexes
    search_results = await orchestrate_search(text, intent)

    # Step 4: Run agent loop with search context
    response = await run_agent(text, search_results)

    # Step 5: Send response (chunked for Telegram's 4096 limit)
    await send(chat_id, response)
