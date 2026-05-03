"""
Atlas Telegram Bot — DUS Mentörü
FastAPI + Webhook mimarisi, DeepSeek V4 Pro, Pinecone RAG.
Railway'de 7/24 çalışır, bilgisayar kapalıyken bile aktif.
"""

import sys
import os
import logging
import httpx
import cachetools
from fastapi import FastAPI, Request, Response

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.settings import TELEGRAM_TOKEN, ALLOWED_CHAT_IDS, CONVERSATION_TTL_SECONDS, DEEPSEEK_MODEL
from bot.handlers.commands import cmd_start, cmd_help, cmd_stats, cmd_dersler, cmd_sifirla
from bot.handlers.messages import handle_message
from bot.handlers.errors import handle_error

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("atlas_bot")

# ─── FastAPI ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Atlas DUS Mentoru", version="9.0")

# ─── Telegram API ─────────────────────────────────────────────────────────────
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ─── Conversation Context (in-memory TTL cache) ───────────────────────────────
conv_context = cachetools.TTLCache(maxsize=100, ttl=CONVERSATION_TTL_SECONDS)


def get_context(chat_id: int) -> dict:
    if chat_id not in conv_context:
        conv_context[chat_id] = {"history": [], "ders": None}
    return conv_context[chat_id]


def clear_context(chat_id: int) -> None:
    conv_context.pop(chat_id, None)


# ─── Telegram Helpers ─────────────────────────────────────────────────────────
async def send(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    """Send message with auto-chunking for Telegram's 4096 char limit."""
    MAX_LEN = 4000
    parts = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    async with httpx.AsyncClient(timeout=30) as client:
        for i, part in enumerate(parts):
            payload = {"chat_id": chat_id, "text": part}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            if resp.status_code != 200:
                log.error(f"Telegram send hatasi: {resp.status_code} {resp.text[:200]}")
                # Retry without parse_mode if it failed
                if parse_mode:
                    payload.pop("parse_mode", None)
                    await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


async def send_action(chat_id: int, action: str = "typing") -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
        )


async def notify_admin(text: str) -> None:
    """Send alert to Furkan. Uses first allowed chat_id."""
    if ALLOWED_CHAT_IDS:
        admin_id = next(iter(ALLOWED_CHAT_IDS))
        try:
            await send(admin_id, f"🔧 Admin: {text}", parse_mode="")
        except Exception:
            pass


# ─── Auth Guard ───────────────────────────────────────────────────────────────
def is_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True  # No whitelist configured — allow all
    return chat_id in ALLOWED_CHAT_IDS


# ─── Webhook Endpoint ─────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    chat_id = None
    try:
        data = await request.json()
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

        # ─── Commands ───────────────────────────────────────────────────
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

        # ─── Normal Message ──────────────────────────────────────────────
        await handle_message(chat_id, text, send, send_action, ctx)

    except Exception as e:
        log.error(f"Webhook hatasi: {e}", exc_info=True)
        if chat_id:
            try:
                await handle_error(chat_id, e, send)
            except Exception:
                pass

    return Response(status_code=200)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/")
async def health():
    return {
        "status": "ok",
        "bot": "Atlas DUS Mentörü",
        "version": "9.0",
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


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info(f"Atlas Bot v9.0 baslatiliyor... Model: {DEEPSEEK_MODEL}")
    if ALLOWED_CHAT_IDS:
        log.info(f"Whitelist: {ALLOWED_CHAT_IDS}")

    # Set webhook on startup
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    if base_url:
        webhook_url = f"{base_url}/webhook"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message", "edited_message"]},
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
    # Delete webhook on shutdown
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/deleteWebhook")
    log.info("Webhook silindi.")


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
