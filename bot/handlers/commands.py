import logging
from bot.deps import mybrain_idx, myppdfs_idx, anki_idx, supabase
from bot.settings import DEEPSEEK_MODEL, AVAILABLE_MODELS, SPEED_MODE_CONFIG

log = logging.getLogger(__name__)


async def cmd_start(chat_id: int, send) -> None:
    await send(chat_id,
        "Selam Furkan! Ben Atlas, DUS Mentorun.\n\n"
        "✅ Tum ders notlarina erisebilirim\n"
        "✅ Hafizani sorgulayabilirim\n"
        "✅ 16.000+ DUS sorusu bankasinda arama yapabilirim\n"
        "✅ Anki kartlarina ulasabilirim\n\n"
        "Ne yapmak istersin?\n"
        "- Konu anlatimi: \"SCC patogenezini anlat\"\n"
        "- Soru cozumu: \"Periodontoloji sorularina bakalim\"\n"
        "- Ilerleme: \"En son ne calismistim?\"\n"
        "- Cikmis analiz: \"Patolojide en cok cikan konular\"\n\n"
        "Prefix komutlari:\n"
        "/mypdf - Dogrudan ders notlarinda ara\n"
        "/brain - Dogrudan hafizada ara\n"
        "/soru - Dogrudan soru coz\n"
        "/anki - Dogrudan Anki kartlarinda ara\n"
        "/cikmis - Dogrudan cikmis analizi yap\n\n"
        "/ayarlar - Bot ayarlari\n"
        "/stats - Sistem durumu\n"
        "/dersler - Brans listesi\n"
        "/sifirla - Sohbeti temizle",
        parse_mode=""
    )


async def cmd_help(chat_id: int, send) -> None:
    await cmd_start(chat_id, send)


async def cmd_stats(chat_id: int, send) -> None:
    try:
        sm = mybrain_idx.describe_index_stats()
        sp = myppdfs_idx.describe_index_stats()
        sa = anki_idx.describe_index_stats()
        sq = supabase.table("questions").select("id", count="exact").limit(1).execute()

        ns_m = sm.get("namespaces", {})
        ns_p = sp.get("namespaces", {})
        ns_a = sa.get("namespaces", {})

        text = (
            "📊 *Sistem Durumu*\n\n"
            f"🧠 *mybrain:* {sm.get('total_vector_count','?')} kayit\n"
            f"  dus-data: {ns_m.get('dus-data',{}).get('vector_count',0)}\n"
            f"  dus-memory: {ns_m.get('dus-memory',{}).get('vector_count',0)}\n"
            f"  dus-progress: {ns_m.get('dus-progress',{}).get('vector_count',0)}\n"
            f"  chathistory: {ns_m.get('chathistory',{}).get('vector_count',0)}\n\n"
            f"🔬 *myppdfs:* {sp.get('total_vector_count','?')} kayit\n"
            f"  patoloji: {ns_p.get('patoloji',{}).get('vector_count',0)}\n"
            f"  radyoloji: {ns_p.get('radyoloji',{}).get('vector_count',0)}\n"
            f"  endodonti: {ns_p.get('endodonti',{}).get('vector_count',0)}\n"
            f"  protez: {ns_p.get('protez',{}).get('vector_count',0)}\n"
            f"  periodontoloji: {ns_p.get('periodontoloji',{}).get('vector_count',0)}\n\n"
            f"🃏 *anki:* {sa.get('total_vector_count','?')} kart\n"
            f"  protez: {ns_a.get('protez',{}).get('vector_count',0)}\n"
            f"  radyoloji: {ns_a.get('radyoloji',{}).get('vector_count',0)}\n\n"
            f"❓ *Soru Bankasi:* {sq.count} soru\n"
            f"🤖 *Model:* {DEEPSEEK_MODEL}\n"
            f"☁️ *Platform:* Railway"
        )
        await send(chat_id, text, parse_mode="Markdown")
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
        "11. Restoratif Dis Tedavisi\n"
        "12. Anatomi\n\n"
        "Ornek: \"Patoloji calismak istiyorum\" veya \"SCC patogenezini anlat\""
    )
    await send(chat_id, text, parse_mode="")


async def cmd_sifirla(chat_id: int, send, clear_context) -> None:
    clear_context(chat_id)
    await send(chat_id, "Sohbet temizlendi, hafiza sifirlandi.")


async def cmd_settings(chat_id: int, send, get_settings, update_settings) -> None:
    """Show settings menu with inline keyboard."""
    settings = get_settings(chat_id)
    speed_mode = settings.get("speed_mode", "balanced")
    model = settings.get("model", "deepseek-chat")
    depth = settings.get("search_depth", 5)

    spd_label = SPEED_MODE_CONFIG.get(speed_mode, {}).get("label", speed_mode)
    model_label = AVAILABLE_MODELS.get(model, model)
    rerank_status = "✅" if settings.get("rerank_enabled", True) else "❌"

    text = (
        "⚙️ *Atlas Bot Ayarlari*\n\n"
        f"🚀 *Hiz Modu:* {spd_label}\n"
        f"🤖 *Model:* {model_label}\n"
        f"🔍 *Arama Derinligi:* {depth} sonuc\n"
        f"📊 *Reranking:* {rerank_status}\n\n"
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
                {"text": "🧠 Reasoner (Doğru)", "callback_data": "settings:model:deepseek-reasoner"},
                {"text": "⚡ V4 Pro (Hızlı)", "callback_data": "settings:model:deepseek-chat"},
            ],
            [
                {"text": "🔍 -1 Derinlik", "callback_data": "settings:depth:down"},
                {"text": "🔍 +1 Derinlik", "callback_data": "settings:depth:up"},
            ],
            [
                {"text": "📊 Rerank: Aç/Kapat", "callback_data": "settings:toggle:rerank"},
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
