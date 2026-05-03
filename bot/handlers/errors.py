import logging
import traceback

log = logging.getLogger(__name__)


async def handle_error(chat_id: int, error: Exception, send) -> None:
    """Global error handler — log and notify user."""
    log.error(f"Bot hatasi (chat={chat_id}): {error}", exc_info=True)

    msg = str(error)[:200]
    if "429" in str(error).upper() or "RATE" in str(error).upper():
        user_msg = "Atlas su an yogun, lutfen biraz bekleyip tekrar dene."
    elif "TIMEOUT" in str(error).upper() or "timeout" in str(error).lower():
        user_msg = "Arama zaman asimina ugradi. Lutfen daha kisa bir sorgu dene."
    elif "AUTH" in str(error).upper() or "401" in str(error):
        user_msg = "Servis kimlik dogrulama hatasi. Admin kontrol edecek."
    else:
        user_msg = f"Bir hata olustu: {msg}"

    try:
        await send(chat_id, user_msg, parse_mode="")
    except Exception:
        log.error("Hata mesaji gonderilemedi.")
