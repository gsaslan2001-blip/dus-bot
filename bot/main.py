"""
Atlas Telegram Bot — DUS Mentoru
FastAPI + Webhook mimarisi, DeepSeek V4 Pro, Pinecone RAG.
Railway'de 7/24 calisir, bilgisayar kapaliyken bile aktif.
v9.2: Ayarlar menusu, hiz optimizasyonlari, cache, rerank iyilestirmeleri
"""

import sys
import os
import logging
import httpx
import cachetools
from fastapi import FastAPI, Request, Response

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.settings import (
    TELEGRAM_TOKEN, ALLOWED_CHAT_IDS, CONVERSATION_TTL_SECONDS,
    DEEPSEEK_MODEL, USER_SETTINGS_DEFAULTS,
)
from bot.handlers.commands import (
    cmd_start, cmd_help, cmd_stats, cmd_dersler, cmd_sifirla,
    cmd_settings, handle_settings_callback,
)
from bot.handlers.messages import handle_message
from bot.handlers.errors import handle_error

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("atlas_bot")

# --- FastAPI ---
app = FastAPI(title="Atlas DUS Mentoru", version="9.2")

# --- Telegram API ---
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# --- Conversation Context (in-memory TTL cache) ---
conv_context = cachetools.TTLCache(maxsize=100, ttl=CONVERSATION_TTL_SECONDS)

# --- User Settings (in-memory TTL cache) ---
user_settings = cachetools.TTLCache(maxsize=100, ttl=CONVERSATION_TTL_SECONDS * 24)

# --- Search Result Cache (5 min TTL for speed) ---
search_cache = cachetools.TTLCache(maxsize=200, ttl=300)


def get_context(chat_id: int) -> dict:
    if chat_id not in conv_context:
        conv_context[chat_id] = {"history": [], "ders": None}
    return conv_context[chat_id]


def clear_context(chat_id: int) -> None:
    conv_context.pop(chat_id, None)


def get_settings(chat_id: int) -> dict:
    if chat_id not in user_settings:
        user_settings[chat_id] = USER_SETTINGS_DEFAULTS.copy()
    return user_settings[chat_id]


def update_settings(chat_id: int, new_settings: dict) -> None:
    user_settings[chat_id] = new_settings


def get_search_cache_key(query: str, intent: str, forced_index: str | None) -> str:
    return f"{query[:100]}|{intent}|{forced_index or ''}"


# --- Telegram Helpers ---
async def send(chat_id: int, text: str, parse_mode: str = "Markdown", reply_markup: str = None) -> None:
    """Send message with auto-chunking for Telegram's 4096 char limit."""
    MAX_LEN = 4000
    parts = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    async with httpx.AsyncClient(timeout=30) as client:
        for i, part in enumerate(parts):
            payload = {"chat_id": chat_id, "text": part}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            # Only attach reply_markup to first chunk
            if reply_markup and i == 0:
                payload["reply_markup"] = reply_markup
            resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            if resp.status_code != 200:
                log.error(f"Telegram send hatasi: {resp.status_code} {resp.text[:200]}")
                # Retry without parse_mode if it failed
                if parse_mode:
                    payload.pop("parse_mode", None)
                    payload.pop("reply_markup", None)
                    await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


async def send_action(chat_id: int, action: str = "typing") -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
        )


async def answer_callback(callback_id: str, text: str, show_alert: bool = False) -> None:
    """Answer a callback query with a toast or alert."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={
                "callback_query_id": callback_id,
                "text": text,
                "show_alert": show_alert,
            },
        )


async def notify_admin(text: str) -> None:
    """Send alert to Furkan. Uses first allowed chat_id."""
    if ALLOWED_CHAT_IDS:
        admin_id = next(iter(ALLOWED_CHAT_IDS))
        try:
            await send(admin_id, f"Admin: {text}", parse_mode="")
        except Exception:
            pass


# --- Auth Guard ---
def is_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS


# --- Webhook Endpoint ---
@app.post("/webhook")
async def webhook(request: Request):
    chat_id = None
    try:
        data = await request.json()

        # --- Callback Query (inline keyboard) ---
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_id = cq.get("id", "")
            cb_data = cq.get("data", "")
            cb_chat = cq.get("message", {}).get("chat", {})
            cb_chat_id = cb_chat.get("id")
            cb_user = cq.get("from", {})
            cb_user_id = cb_user.get("id", 0)

            if cb_chat_id and cb_data:
                log.info(f"[CALLBACK] chat={cb_chat_id} data={cb_data} id={cb_id}")
                await handle_settings_callback(
                    cb_chat_id, cb_data, cb_user_id, cb_id,
                    send, answer_callback, get_settings, update_settings
                )
            return Response(status_code=200)

        message = data.get("message") or data.get("edited_message", {})
        if not message:
            return Response(status_code=200)

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()
        if not chat_id or not text:
            return Response(status_code=200)

        # Auth check
        if not is_allowed(chat_id):
            log.warning(f"Unauthorized chat_id: {chat_id}")
            await send(chat_id, "Bu bot ozel kullanim icindir. Erisim yetkiniz yok.", parse_mode="")
            return Response(status_code=200)

        log.info(f"[MSG] chat={chat_id} text={text[:100]}")

        # Get or create context
        ctx = get_context(chat_id)

        # --- Commands ---
        if text.startswith("/start"):
            await cmd_start(chat_id, send)
            return Response(status_code=200)

        if text.startswith("/help"):
            await cmd_help(chat_id, send)
            return Response(status_code=200)

        if text.startswith("/stats"):
            await send_action(chat_id, "typing")
            await cmd_stats(chat_id, send)
            return Response(status_code=200)

        if text.startswith("/dersler"):
            await cmd_dersler(chat_id, send)
            return Response(status_code=200)

        if text.startswith("/sifirla"):
            await cmd_sifirla(chat_id, send, clear_context)
            return Response(status_code=200)

        if text.startswith("/ayarlar") or text.startswith("/settings"):
            await cmd_settings(chat_id, send, get_settings, update_settings)
            return Response(status_code=200)

        # --- Normal Message ---
        await handle_message(
            chat_id, text, send, send_action, ctx,
            get_settings, search_cache, get_search_cache_key,
        )

    except Exception as e:
        log.error(f"Webhook hatasi: {e}", exc_info=True)
        if chat_id:
            try:
                await handle_error(chat_id, e, send)
            except Exception:
                pass

    return Response(status_code=200)


# --- Health Check ---
@app.get("/")
async def health():
    return {
        "status": "ok",
        "bot": "Atlas DUS Mentoru",
        "version": "9.2",
        "model": DEEPSEEK_MODEL,
    }


@app.get("/health")
async def health_detailed():
    try:
        from bot.deps import mybrain_idx, supabase, deepseek
        sm = mybrain_idx.describe_index_stats()
        pinecone_ok = sm.get("total_vector_count", 0) > 0
    except Exception:
        pinecone_ok = False
    try:
        sq = supabase.table("questions").select("id", count="exact").limit(1).execute()
        supabase_ok = sq.count > 0
    except Exception:
        supabase_ok = False

    return {
        "status": "ok" if (pinecone_ok and supabase_ok) else "degraded",
        "pinecone": pinecone_ok,
        "supabase": supabase_ok,
        "deepseek_model": DEEPSEEK_MODEL,
    }


# --- Startup ---
@app.on_event("startup")
async def startup():
    log.info(f"Atlas Bot v9.2 baslatiliyor... Model: {DEEPSEEK_MODEL}")
    if ALLOWED_CHAT_IDS:
        log.info(f"Whitelist: {ALLOWED_CHAT_IDS}")

    # Set webhook on startup
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    if base_url:
        webhook_url = f"{base_url}/webhook"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message", "edited_message", "callback_query"]},
            )
            result = resp.json()
            if result.get("ok"):
                log.info(f"Webhook basariyla kuruldu: {webhook_url}")
            else:
                log.error(f"Webhook kurulum hatasi: {result}")
    else:
        log.warning("BASE_URL ayarlanmamis, webhook kurulamadi. Railway'de otomatik ayarlanir.")


@app.on_event("shutdown")
async def shutdown():
    log.info("Atlas Bot kapatiliyor...")
    # Webhook silinmiyor — yeni instance startup'ta zaten üzerine yazar.
    # Silme, Railway deploy sırasında mesaj kaybına yol açıyordu.


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
