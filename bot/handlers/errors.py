import logging
import traceback

log = logging.getLogger(__name__)


async def handle_error(chat_id: int, error: Exception, send) -> None:
    """Global error handler — log and notify user."""
    log.error(f"Bot hatasi (chat={chat_id}): {error}", exc_info=True)

    err_str = str(error).upper()
    if "429" in err_str or "RATE" in err_str:
        user_msg = "Atlas su an yogun, lutfen biraz bekleyip tekrar dene."
    elif "TIMEOUT" in err_str:
        user_msg = "Arama zaman asimina ugradi. Lutfen daha kisa bir sorgu dene."
    elif "AUTH" in err_str or "401" in err_str:
        user_msg = "Servis kimlik dogrulama hatasi. Admin kontrol edecek."
    else:
        # Ic hata metnini kullaniciya sizdirma — detay sadece sunucu logunda
        user_msg = "Beklenmeyen bir hata olustu, lutfen tekrar dene."

    try:
        await send(chat_id, user_msg, parse_mode="")
    except Exception:
        log.error("Hata mesaji gonderilemedi.")
