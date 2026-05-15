import asyncio
import logging
import re
from typing import Optional

from scripts.search_engine import (
    pinecone_search,
    search_multi_ns,
    search_anki_multi_ns,
    search_questions,
    SEARCH_TIMEOUT,
    _with_timeout,
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

# myppdfs namespace listesi (mevcut 11 namespace — restoratif yok)
PDFS_NAMESPACES = [
    "patoloji", "radyoloji", "endodonti", "protez", "histoloji",
    "fizyoloji", "periodontoloji", "cerrahi", "farmakoloji",
    "pedodonti", "cikmis",
]

# mybrain namespace listesi (tüm mevcut namespace'ler — 943 kayıt)
BRAIN_NAMESPACES = [
    "dus-memory", "dus-progress", "dus-strategy", "dus-reference",
    "dus-curriculum", "chathistory", "telos", "claude-profile",
]

# anki namespace listesi (tüm mevcut namespace'ler — 13064 kart)
ANKI_NAMESPACES = [
    "histoloji", "periodontoloji", "protez", "fizyoloji",
    "radyoloji", "patoloji", "endodonti",
]

_TR_LOWER = str.maketrans("İIĞÜŞÇÖ", "iiğüşçö")


def _normalize_tr(text: str) -> str:
    return text.translate(_TR_LOWER).lower()


def _detect_ders(query: str) -> Optional[str]:
    """Sorgu metninden hangi branşın sorulduğunu tespit et (word-boundary matching)."""
    ders_keywords = {
        "patoloji": ["patoloji", "tümör", "tumor", "neoplazi", "karsinom", "sarkom", "inflamasyon", "lezyon", r"\bkist\b"],
        "radyoloji": ["radyoloji", "radyografi", r"\bx-ray\b", "görüntüleme", "goruntuleme", "radyasyon", r"\bkvp\b", r"\bmas\b", "panoramik", "periapikal"],
        "endodonti": ["endodonti", "kanal tedavisi", "pulpa", "kök kanal", "kok kanal", r"\beğe\b", r"\bfile\b", "apeks", r"\bguta\b", "perforasyon", r"\bsaf\b"],
        "protez": ["protez", "kuron", "köprü", "kopru", "implant", "porselen", "akrilik", "oklüzyon", "okluzyon", "veneer"],
        "histoloji": ["histoloji", "doku", "epitel", "bağ doku", "bag doku", "embriyoloji", "mine", "dentin", "sement"],
        "fizyoloji": ["fizyoloji", "fonksiyon", "homeostaz", "potansiyel", "iletim"],
        "periodontoloji": ["periodontoloji", "periodontal", "diş eti", "dis eti", "gingiva", r"\bcep\b", "ataşman", "ataman", "detertraj"],
        "cerrahi": ["cerrahi", "çekim", "cekim", "anestezi", "greft", "sinüs", "sinus", "rezedans"],
        "farmakoloji": ["farmakoloji", r"\bilaç\b", r"\bilac\b", "antibiyotik", "analjezik", "agonist", "antagonist"],
        "pedodonti": ["pedodonti", "çocuk", "cocuk", "süt dişi", "sut disi", "pediatrik", "fissür", "fissur"],
        "restoratif": ["restoratif", "dolgu", "kompozit", "amalgam", "adeziv", "bonding", "kavit"],
    }
    query_norm = _normalize_tr(query)
    for ders, keywords in ders_keywords.items():
        for kw in keywords:
            if kw.startswith(r"\b"):
                # Regex word boundary match
                if re.search(kw, query_norm):
                    return ders
            elif kw in query_norm:
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
    rerank_enabled = settings.get("rerank_enabled", True)
    is_fast = speed_mode == "fast"

    coros: dict[str, object] = {}
    ders = _detect_ders(query)
    brain_top_k = 4 if is_fast else 6
    top_k = 6 if is_fast else 8

    # ── EXCLUSIVE: Prefix komutu varsa sadece o index ────────────────────────

    if forced_index == "dusbankasi":
        # Sadece soru bankası — /soru komutu (pure semantic, ders filtresi yok)
        q_limit = min(search_depth, 8)
        coros["questions"] = asyncio.to_thread(search_questions, query, None, q_limit, rerank_enabled)

    elif forced_index == "mybrain":
        # Sadece hafıza — /brain komutu
        coros["brain"] = search_multi_ns(query, "mybrain", BRAIN_NAMESPACES, brain_top_k, search_depth)

    elif forced_index == "anki":
        # Sadece Anki — /anki komutu (OpenAI 3072-dim, integrated search yok)
        ns_list = [ders] if ders in ANKI_NAMESPACES else ANKI_NAMESPACES
        coros["anki"] = search_anki_multi_ns(
            query, ns_list, top_k, search_depth, rerank_enabled
        )

    elif forced_index == "myppdfs":
        # Sadece ders notları — /mypdf komutu
        namespaces = [ders] if ders and ders in PDFS_NAMESPACES else PDFS_NAMESPACES[:6]
        cross = CROSS_NS_MAP.get(ders, []) if ders else []
        all_ns = list(dict.fromkeys(namespaces + cross))
        if is_fast and ders:
            all_ns = [ders]
        if len(all_ns) > 1:
            coros["pdfs"] = search_multi_ns(query, "myppdfs", all_ns, top_k, search_depth, rerank_enabled)
        else:
            coros["pdfs"] = asyncio.to_thread(
                pinecone_search, query, "myppdfs", all_ns[0], top_k, search_depth, rerank_enabled
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
                coros["pdfs"] = search_multi_ns(query, "myppdfs", all_ns, top_k, search_depth, rerank_enabled)
            else:
                coros["pdfs"] = asyncio.to_thread(
                    pinecone_search, query, "myppdfs", all_ns[0], top_k, search_depth, rerank_enabled
                )

        # mybrain: hafıza ve genel intent'te
        brain_should_search = intent in ("hafiza", "genel")
        if brain_should_search and not (is_fast and intent == "genel" and ders is not None):
            coros["brain"] = search_multi_ns(
                query, "mybrain", BRAIN_NAMESPACES, brain_top_k, search_depth, rerank_enabled
            )

        # Soru bankası: ders çalışma, soru çözme, çıkmış analizi (pure semantic, ders filtresi yok)
        if intent in ("ders_calis", "soru_sor", "cikmis_analiz"):
            q_limit = min(search_depth, 5)
            coros["questions"] = asyncio.to_thread(search_questions, query, None, q_limit, rerank_enabled)

        # Anki: hızlı mod değilse ve bilinen anki branşıysa
        if not is_fast and ders in ANKI_NAMESPACES:
            ns_list = [ders]
            coros["anki"] = search_anki_multi_ns(
                query, ns_list, 8, min(search_depth, 3), rerank_enabled
            )

    # Tüm aramaları gerçekten paralel başlat (timeout korumalı)
    tasks = {key: asyncio.create_task(coro) for key, coro in coros.items()}

    results = {}
    for key, task in tasks.items():
        try:
            results[key] = await _with_timeout(task, SEARCH_TIMEOUT, f"orchestrator:{key}")
        except Exception as e:
            log.warning(f"[orchestrator] {key} arama hatasi: {e}")
            results[key] = []

    log.info(
        f"[orchestrator] intent={intent} forced={forced_index} ders={ders} speed={speed_mode} "
        f"pdfs={len(results.get('pdfs', []))} brain={len(results.get('brain', []))} "
        f"questions={len(results.get('questions', []))} anki={len(results.get('anki', []))}"
    )

    return results
