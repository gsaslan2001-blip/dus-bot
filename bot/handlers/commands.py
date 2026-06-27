import logging
from bot.deps import myppdfs_idx, dusbankasi_idx
from bot.settings import DEEPSEEK_MODEL, AVAILABLE_MODELS, SPEED_MODE_CONFIG

log = logging.getLogger(__name__)


async def cmd_start(chat_id: int, send) -> None:
    await send(chat_id,
        "Selam Furkan! Ben Atlas, DUS Mentorun.\n\n"
        "Dogrudan soru sorabilirsin:\n"
        "  \"SCC patogenezini anlat\"\n"
        "  \"Periodontoloji sorularina bakalim\"\n\n"
        "Index yonlendirme komutlari (nerede arayacagimi belirtir):\n"
        "  /mypdf [konu]  - Ders notlarinda ara (myppdfs)\n"
        "  /soru [konu]   - Soru bankasinda ara (~20.000 soru)\n\n"
        "Ornek: \"/soru amiloblastom\" -> sadece soru bankasinda arar\n"
        "Ornek: \"/mypdf periodontit\" -> sadece ders notlarinda arar\n\n"
        "Diger komutlar:\n"
        "  /ayarlar - Hiz modu, model, arama derinligi\n"
        "  /stats   - Index istatistikleri\n"
        "  /dersler - Brans listesi\n"
        "  /sifirla - Sohbeti temizle",
        parse_mode=""
    )


async def cmd_help(chat_id: int, send) -> None:
    await cmd_start(chat_id, send)


def _ns_count(ns_dict: dict, key: str) -> int:
    """Pinecone describe_index_stats namespaces dict'ten kayit sayisi al."""
    ns = ns_dict.get(key, {})
    if isinstance(ns, dict):
        return ns.get("vector_count", ns.get("recordCount", 0))
    return getattr(ns, "vector_count", getattr(ns, "record_count", 0))


def _total_count(stats) -> str:
    if isinstance(stats, dict):
        return str(stats.get("total_vector_count", stats.get("totalRecordCount", "?")))
    return str(getattr(stats, "total_vector_count", getattr(stats, "total_record_count", "?")))


def _get_namespaces(stats) -> dict:
    if isinstance(stats, dict):
        return stats.get("namespaces", {})
    return getattr(stats, "namespaces", {}) or {}


async def cmd_stats(chat_id: int, send) -> None:
    try:
        sp = myppdfs_idx.describe_index_stats()
        sd = dusbankasi_idx.describe_index_stats()

        ns_p = _get_namespaces(sp)
        ns_d = _get_namespaces(sd)

        # dusbankasi default namespace (bos string key)
        q_count = _ns_count(ns_d, "") or _ns_count(ns_d, "__default__")

        text = (
            "Sistem Durumu\n\n"
            f"myppdfs: {_total_count(sp)} kayit\n"
            f"  patoloji: {_ns_count(ns_p, 'patoloji')}\n"
            f"  radyoloji: {_ns_count(ns_p, 'radyoloji')}\n"
            f"  endodonti: {_ns_count(ns_p, 'endodonti')}\n"
            f"  protez: {_ns_count(ns_p, 'protez')}\n"
            f"  histoloji: {_ns_count(ns_p, 'histoloji')}\n"
            f"  fizyoloji: {_ns_count(ns_p, 'fizyoloji')}\n"
            f"  periodontoloji: {_ns_count(ns_p, 'periodontoloji')}\n"
            f"  cerrahi: {_ns_count(ns_p, 'cerrahi')}\n"
            f"  farmakoloji: {_ns_count(ns_p, 'farmakoloji')}\n"
            f"  pedodonti: {_ns_count(ns_p, 'pedodonti')}\n"
            f"  ortodonti: {_ns_count(ns_p, 'ortodonti')}\n"
            f"  cikmis: {_ns_count(ns_p, 'cikmis')}\n\n"
            f"Soru Bankasi (dusbankasi): {q_count} soru\n"
            f"Model: {DEEPSEEK_MODEL}\n"
            f"Platform: Railway"
        )
        await send(chat_id, text, parse_mode="")
    except Exception as e:
        await send(chat_id, f"Istatistik hatasi: {e}", parse_mode="")


async def cmd_dersler(chat_id: int, send) -> None:
    text = (
        "DUS Branslari\n\n"
        "1. Patoloji\n"
        "2. Radyoloji\n"
        "3. Endodonti\n"
        "4. Protez\n"
        "5. Histoloji & Embriyoloji\n"
        "6. Fizyoloji\n"
        "7. Periodontoloji\n"
        "8. Agiz Dis Cene Cerrahisi\n"
        "9. Farmakoloji\n"
        "10. Pedodonti\n"
        "11. Ortodonti\n"
        "12. Restoratif Dis Tedavisi\n"
        "13. Anatomi\n\n"
        "Ornek: \"Patoloji calismak istiyorum\" veya \"SCC patogenezini anlat\""
    )
    await send(chat_id, text, parse_mode="")


async def cmd_sifirla(chat_id: int, send, clear_context) -> None:
    clear_context(chat_id)
    await send(chat_id, "Sohbet temizlendi.")


async def cmd_settings(chat_id: int, send, get_settings, update_settings) -> None:
    """Show settings menu with inline keyboard."""
    settings = get_settings(chat_id)
    speed_mode = settings.get("speed_mode", "balanced")
    model = settings.get("model", "deepseek-v4-pro")
    depth = settings.get("search_depth", 5)

    spd_label = SPEED_MODE_CONFIG.get(speed_mode, {}).get("label", speed_mode)
    model_label = AVAILABLE_MODELS.get(model, model)

    text = (
        "⚙️ *Atlas Bot Ayarlari*\n\n"
        f"🚀 *Hiz Modu:* {spd_label}\n"
        f"🤖 *Model:* {model_label}\n"
        f"🔍 *Arama Derinligi:* {depth} sonuc\n\n"
        "Asagidaki dugmelerden ayarlari degistirebilirsin:"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🚀 Hızlı Mod", "callback_data": "settings:speed:fast"},
                {"text": "⚖️ Dengeli", "callback_data": "settings:speed:balanced"},
                {"text": "🔬 Kapsamlı", "callback_data": "settings:speed:comprehensive"},
            ],
            [
                {"text": "⚡ V4 Pro (Güçlü)", "callback_data": "settings:model:deepseek-v4-pro"},
                {"text": "🪶 V4 Flash (Hızlı)", "callback_data": "settings:model:deepseek-chat"},
            ],
            [
                {"text": "🔍 -1 Derinlik", "callback_data": "settings:depth:down"},
                {"text": "🔍 +1 Derinlik", "callback_data": "settings:depth:up"},
            ],
            [
                {"text": f"🔁 Rerank: {'AÇIK' if settings.get('rerank_enabled', True) else 'KAPALI'}", "callback_data": "settings:toggle:rerank"},
            ],
            [
                {"text": "🔄 Sıfırla", "callback_data": "settings:reset"},
            ],
            [
                {"text": "❌ Kapat", "callback_data": "settings:close"},
            ],
        ]
    }

    import json
    await send(chat_id, text, parse_mode="Markdown", reply_markup=json.dumps(keyboard))


async def handle_settings_callback(chat_id: int, callback_data: str, user_id: int, callback_id: str,
                                   send, answer_callback, get_settings, update_settings) -> None:
    """Handle settings inline keyboard callbacks."""
    parts = callback_data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "close":
        await answer_callback(callback_id, "Menu kapatildi")
        return

    if action == "reset":
        from bot.settings import USER_SETTINGS_DEFAULTS
        update_settings(chat_id, USER_SETTINGS_DEFAULTS.copy())
        await answer_callback(callback_id, "Ayarlar sifirlandi!")
        await cmd_settings(chat_id, send, get_settings, update_settings)
        return

    settings = get_settings(chat_id)

    if action == "speed":
        mode = parts[2]
        from bot.settings import SPEED_MODE_CONFIG
        if mode in SPEED_MODE_CONFIG:
            cfg = SPEED_MODE_CONFIG[mode]
            settings["speed_mode"] = mode
            settings["agent_iterations"] = cfg["agent_iterations"]
            settings["search_depth"] = cfg["search_depth"]
            settings["rerank_enabled"] = cfg["rerank_enabled"]
            update_settings(chat_id, settings)
            await answer_callback(callback_id, f"Hiz modu: {cfg['label']}")
            await cmd_settings(chat_id, send, get_settings, update_settings)

    elif action == "model":
        model = parts[2]
        if model in AVAILABLE_MODELS:
            settings["model"] = model
            update_settings(chat_id, settings)
            await answer_callback(callback_id, f"Model: {AVAILABLE_MODELS[model]}")
            await cmd_settings(chat_id, send, get_settings, update_settings)

    elif action == "depth":
        direction = parts[2]
        current = settings.get("search_depth", 5)
        if direction == "up":
            settings["search_depth"] = min(10, current + 1)
        elif direction == "down":
            settings["search_depth"] = max(2, current - 1)
        update_settings(chat_id, settings)
        await answer_callback(callback_id, f"Arama derinligi: {settings['search_depth']}")
        await cmd_settings(chat_id, send, get_settings, update_settings)

    elif action == "toggle":
        target = parts[2]
        if target == "rerank":
            settings["rerank_enabled"] = not settings.get("rerank_enabled", True)
            update_settings(chat_id, settings)
            status = "✅" if settings["rerank_enabled"] else "❌"
            await answer_callback(callback_id, f"Reranking: {status}")
            await cmd_settings(chat_id, send, get_settings, update_settings)
