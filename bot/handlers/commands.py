import logging
from bot.deps import mybrain_idx, myppdfs_idx, anki_idx, supabase
from bot.settings import DEEPSEEK_MODEL

log = logging.getLogger(__name__)


async def cmd_start(chat_id: int, send) -> None:
    await send(chat_id,
        "Selam Furkan! Ben *Atlas*, DUS Mentörün.\n\n"
        "\\✅ Tum ders notlarina erisebilirim\n"
        "\\✅ Hafizani sorgulayabilirim\n"
        "\\✅ 16.000\\+ DUS sorusu bankasinda arama yapabilirim\n"
        "\\✅ Anki kartlarina ulasabilirim\n\n"
        "**Ne yapmak istersin?**\n"
        "\\- Konu anlatimi: _\"SCC patogenezini anlat\"_\n"
        "\\- Soru cozumu: _\"Periodontoloji sorularina bakalim\"_\n"
        "\\- Ilerleme: _\"En son ne calismistim?\"_\n"
        "\\- Cikmis analiz: _\"Patolojide en cok cikan konular\"_\n\n"
        "**Mesaj basinda prefix'ler:**\n"
        "/mypdf \\- Dogrudan ders notlarinda ara\n"
        "/brain \\- Dogrudan hafizada ara\n"
        "/soru \\- Dogrudan soru coz\n"
        "/anki \\- Dogrudan Anki kartlarinda ara\n"
        "/cikmis \\- Dogrudan cikmis analizi yap\n\n"
        "/stats \\- Sistem durumu\n"
        "/dersler \\- Brans listesi\n"
        "/sifirla \\- Sohbeti temizle",
        parse_mode="Markdown"
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
        "📚 *DUS Branslari*\n\n"
        "1\\. Patoloji\n"
        "2\\. Radyoloji\n"
        "3\\. Endodonti\n"
        "4\\. Protez\n"
        "5\\. Histoloji & Embriyoloji\n"
        "6\\. Fizyoloji\n"
        "7\\. Periodontoloji\n"
        "8\\. Agiz Dis Cene Cerrahisi\n"
        "9\\. Farmakoloji\n"
        "10\\. Pedodonti\n"
        "11\\. Restoratif Dis Tedavisi\n"
        "12\\. Anatomi\n\n"
        "Ornek: _\"Patoloji calismak istiyorum\"_ veya _\"SCC patogenezini anlat\"_"
    )
    await send(chat_id, text, parse_mode="Markdown")


async def cmd_sifirla(chat_id: int, send, clear_context) -> None:
    clear_context(chat_id)
    await send(chat_id, "Sohbet temizlendi, hafiza sifirlandi.")
