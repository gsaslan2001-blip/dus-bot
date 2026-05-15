import asyncio
import logging
from typing import Optional

from scripts.search_engine import (
    pinecone_search,
    search_multi_ns,
    search_questions,
)

log = logging.getLogger(__name__)

# İlişkili branşlar — çapraz namespace araması için
CROSS_NS_MAP = {
    "patoloji": ["radyoloji"],
    "radyoloji": ["patoloji", "cerrahi"],
    "cerrahi": ["radyoloji", "anatomi"],
    "endodonti": ["restoratif"],
    "restoratif": ["endodonti"],
    "protez": ["periodontoloji"],
    "periodontoloji": ["protez"],
    "histoloji": ["fizyoloji"],
    "fizyoloji": ["histoloji", "biyokimya"],
}

# myppdfs namespace listesi
PDFS_NAMESPACES = [
    "patoloji", "radyoloji", "endodonti", "protez", "histoloji",
    "fizyoloji", "periodontoloji", "cerrahi", "farmakoloji",
    "pedodonti", "restoratif", "cikmis",
]

# mybrain namespace listesi
BRAIN_NAMESPACES = [
    "dus-memory", "dus-progress", "dus-strategy", "dus-reference",
    "dus-curriculum", "chathistory", "telos",
]

# anki namespace listesi
ANKI_NAMESPACES = ["protez", "radyoloji"]

_TR_LOWER = str.maketrans("İIĞÜŞÇÖ", "iiğüşçö")


def _normalize_tr(text: str) -> str:
    return text.translate(_TR_LOWER).lower()


def _detect_ders(query: str) -> Optional[str]:
    """Sorgu metninden hangi branşın sorulduğunu tespit et."""
    ders_keywords = {
        "patoloji": ["patoloji", "tümör", "tumor", "neoplazi", "karsinom", "sarkom", "inflamasyon"],
        "radyoloji": ["radyoloji", "radyografi", "x-ray", "görüntüleme", "goruntuleme", "radyasyon"],
        "endodonti": ["endodonti", "kanal tedavisi", "pulpa", "kök kanal", "kok kanal"],
        "protez": ["protez", "kuron", "köprü", "kopru", "implant"],
        "histoloji": ["histoloji", "doku", "epitel", "bağ doku", "bag doku", "embriyoloji"],
        "fizyoloji": ["fizyoloji", "fonksiyon", "homeostaz"],
        "periodontoloji": ["periodontoloji", "periodontal", "diş eti", "dis eti", "gingiva"],
        "cerrahi": ["cerrahi", "çekim", "cekim", "anestezi"],
        "farmakoloji": ["farmakoloji", "ilaç", "ilac", "antibiyotik", "analjezik"],
        "pedodonti": ["pedodonti", "çocuk", "cocuk", "süt dişi", "sut disi", "pediatrik"],
        "restoratif": ["restoratif", "dolgu", "kompozit", "amalgam"],
    }
    query_norm = _normalize_tr(query)
    for ders, keywords in ders_keywords.items():
        for kw in keywords:
            if kw in query_norm:
                return ders
    return None


async def orchestrate_search(query: str, intent: str, forced_index: str | None = None,
                             settings: dict | None = None) -> dict:
    """Intent ve prefix routing'e göre paralel arama orkestrasyonu.

    forced_index ayarlandığında SADECE o index'te arama yapılır (exclusive routing).
    Bu, prefix komutlarının alakasız sonuç getirmesini engeller.

    forced_index değerleri:
        "myppdfs"    → sadece ders notları (myppdfs)
        "mybrain"    → sadece hafıza (mybrain)
        "anki"       → sadece Anki kartları
        "dusbankasi" → sadece soru bankası (Pinecone dusbankasi)
        None         → intent bazlı normal yönlendirme
    """
    if settings is None:
        settings = {}

    search_depth = settings.get("search_depth", 5)
    speed_mode = settings.get("speed_mode", "balanced")
    is_fast = speed_mode == "fast"

    coros: dict[str, object] = {}
    ders = _detect_ders(query)
    brain_top_k = 4 if is_fast else 6
    top_k = 6 if is_fast else 8

    # ── EXCLUSIVE: Prefix komutu varsa sadece o index ────────────────────────

    if forced_index == "dusbankasi":
        # Sadece soru bankası — /soru komutu
        q_limit = min(search_depth, 8)
        coros["questions"] = asyncio.to_thread(search_questions, query, ders, q_limit)

    elif forced_index == "mybrain":
        # Sadece hafıza — /brain komutu
        coros["brain"] = search_multi_ns(query, "mybrain", BRAIN_NAMESPACES, brain_top_k, search_depth)

    elif forced_index == "anki":
        # Sadece Anki — /anki komutu
        # Eğer bilinen bir branş namespace'i varsa onu ara, yoksa tüm Anki namespace'lerinde ara
        ns = ders if ders in ANKI_NAMESPACES else None
        if ns:
            coros["anki"] = asyncio.to_thread(
                pinecone_search, query, "anki", ns, 10, search_depth
            )
        else:
            coros["anki"] = search_multi_ns(query, "anki", ANKI_NAMESPACES, top_k, search_depth)

    elif forced_index == "myppdfs":
        # Sadece ders notları — /mypdf komutu
        namespaces = [ders] if ders and ders in PDFS_NAMESPACES else PDFS_NAMESPACES[:6]
        cross = CROSS_NS_MAP.get(ders, []) if ders else []
        all_ns = list(dict.fromkeys(namespaces + cross))
        if is_fast and ders:
            all_ns = [ders]
        if len(all_ns) > 1:
            coros["pdfs"] = search_multi_ns(query, "myppdfs", all_ns, top_k, search_depth)
        else:
            coros["pdfs"] = asyncio.to_thread(
                pinecone_search, query, "myppdfs", all_ns[0], top_k, search_depth
            )

    else:
        # ── NORMAL: Intent bazlı yönlendirme (prefix yok) ────────────────────

        # myppdfs: ders çalışma, soru, çıkmış analizi veya branş tespit edilmişse
        pdfs_should_search = (
            intent in ("ders_calis", "soru_sor", "cikmis_analiz") or
            (intent == "genel" and ders is not None)
        )
        if pdfs_should_search:
            namespaces = [ders] if ders and ders in PDFS_NAMESPACES else PDFS_NAMESPACES[:6]
            cross = CROSS_NS_MAP.get(ders, []) if ders else []
            all_ns = list(dict.fromkeys(namespaces + cross))
            if is_fast and ders:
                all_ns = [ders]
            if len(all_ns) > 1:
                coros["pdfs"] = search_multi_ns(query, "myppdfs", all_ns, top_k, search_depth)
            else:
                coros["pdfs"] = asyncio.to_thread(
                    pinecone_search, query, "myppdfs", all_ns[0], top_k, search_depth
                )

        # mybrain: hafıza ve genel intent'te
        brain_should_search = intent in ("hafiza", "genel")
        if brain_should_search and not (is_fast and intent == "genel" and ders is not None):
            coros["brain"] = search_multi_ns(
                query, "mybrain", BRAIN_NAMESPACES, brain_top_k, search_depth
            )

        # Soru bankası: ders çalışma, soru çözme, çıkmış analizi
        if intent in ("ders_calis", "soru_sor", "cikmis_analiz"):
            q_limit = min(search_depth, 5)
            coros["questions"] = asyncio.to_thread(search_questions, query, ders, q_limit)

        # Anki: hızlı mod değilse ve bilinen anki branşıysa
        if not is_fast and ders in ANKI_NAMESPACES:
            coros["anki"] = asyncio.to_thread(
                pinecone_search, query, "anki", ders, 8, min(search_depth, 3)
            )

    # Tüm aramaları gerçekten paralel başlat
    tasks = {key: asyncio.create_task(coro) for key, coro in coros.items()}

    results = {}
    for key, task in tasks.items():
        try:
            results[key] = await task
        except Exception as e:
            log.warning(f"[orchestrator] {key} arama hatasi: {e}")
            results[key] = []

    log.info(
        f"[orchestrator] intent={intent} forced={forced_index} ders={ders} speed={speed_mode} "
        f"pdfs={len(results.get('pdfs', []))} brain={len(results.get('brain', []))} "
        f"questions={len(results.get('questions', []))} anki={len(results.get('anki', []))}"
    )

    return results
