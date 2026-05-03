import asyncio
import logging
from typing import Optional

from scripts.search_engine import (
    pinecone_search,
    search_multi_ns,
    search_questions,
)

log = logging.getLogger(__name__)

# Cross-namespace map: related branches to search together
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

# myppdfs namespaces
PDFS_NAMESPACES = [
    "patoloji", "radyoloji", "endodonti", "protez", "histoloji",
    "fizyoloji", "periodontoloji", "cerrahi", "farmakoloji",
    "pedodonti", "restoratif", "cikmis",
]

# mybrain namespaces
BRAIN_NAMESPACES = [
    "dus-memory", "dus-progress", "dus-strategy", "dus-reference",
    "dus-curriculum", "chathistory", "telos",
]


def _detect_ders(query: str) -> Optional[str]:
    """Detect which branch the user is asking about from the query text."""
    ders_keywords = {
        "patoloji": ["patoloji", "tumor", "neoplazi", "karsinom", "sarkom", "inflamasyon"],
        "radyoloji": ["radyoloji", "radyografi", "x-ray", "goruntuleme", "radyasyon"],
        "endodonti": ["endodonti", "kanal tedavisi", "pulpa", "kok kanal"],
        "protez": ["protez", "protez", "kuron", "kopru", "implant"],
        "histoloji": ["histoloji", "doku", "epitel", "bag doku", "embriyoloji"],
        "fizyoloji": ["fizyoloji", "fonksiyon", "sistem", "homeostaz"],
        "periodontoloji": ["periodontoloji", "periodontal", "dis eti", "gingiva"],
        "cerrahi": ["cerrahi", "cekim", "anestezi", "cerrahi"],
        "farmakoloji": ["farmakoloji", "ilac", "antibiyotik", "analjezik"],
        "pedodonti": ["pedodonti", "cocuk", "sut disi", "pediatrik"],
        "restoratif": ["restoratif", "dolgu", "kompozit", "amalgam"],
    }
    query_lower = query.lower()
    for ders, keywords in ders_keywords.items():
        for kw in keywords:
            if kw in query_lower:
                return ders
    return None


async def orchestrate_search(query: str, intent: str, forced_index: str | None = None,
                             settings: dict | None = None) -> dict:
    """Run parallel searches across all relevant indexes based on intent.

    Args:
        query: Search query string
        intent: Classified intent (ders_calis, soru_sor, cikmis_analiz, hafiza, genel)
        forced_index: Override index from prefix routing (myppdfs, mybrain, anki, or None)
        settings: User settings dict with speed_mode, search_depth, rerank_enabled
    """
    if settings is None:
        settings = {}

    search_depth = settings.get("search_depth", 5)
    speed_mode = settings.get("speed_mode", "balanced")
    is_fast = speed_mode == "fast"

    coros: dict[str, object] = {}
    ders = _detect_ders(query)

    # --- myppdfs: Always search when ders detected, or for study intents ---
    pdfs_should_search = (
        forced_index == "myppdfs" or
        intent in ("ders_calis", "soru_sor", "cikmis_analiz") or
        (intent == "genel" and ders is not None)
    )
    if pdfs_should_search:
        namespaces = [ders] if ders and ders in PDFS_NAMESPACES else PDFS_NAMESPACES[:6]
        cross = CROSS_NS_MAP.get(ders, []) if ders else []
        all_ns = list(dict.fromkeys(namespaces + cross))
        # Fast mode: skip cross-namespace search, only search detected ders
        if is_fast and ders:
            all_ns = [ders]
        top_k = 10 if is_fast else 15
        if len(all_ns) > 1:
            coros["pdfs"] = search_multi_ns(query, "myppdfs", all_ns, top_k, search_depth)
        else:
            coros["pdfs"] = asyncio.to_thread(
                pinecone_search, query, "myppdfs", all_ns[0], top_k, search_depth
            )

    # --- mybrain: Search for memory/progress intents, or forced ---
    brain_should_search = (
        forced_index == "mybrain" or
        intent in ("hafiza", "genel")
    )
    # Fast mode: skip brain search unless explicitly memory intent
    if brain_should_search and not (is_fast and intent == "genel" and ders is not None):
        brain_top_k = 5 if is_fast else 10
        coros["brain"] = search_multi_ns(query, "mybrain", BRAIN_NAMESPACES, brain_top_k, search_depth)

    # --- Supabase questions: For study and exam analysis ---
    if intent in ("ders_calis", "soru_sor", "cikmis_analiz"):
        q_limit = min(search_depth, 5)
        coros["questions"] = asyncio.to_thread(search_questions, query, ders, q_limit)

    # --- anki: When relevant ders or forced ---
    anki_should_search = (
        forced_index == "anki" or
        (not is_fast and ders in ("protez", "radyoloji"))
    )
    if anki_should_search:
        ns = ders if ders in ("protez", "radyoloji") else "protez"
        coros["anki"] = asyncio.to_thread(
            pinecone_search, query, "anki", ns, 10, min(search_depth, 3)
        )

    # Tüm aramaları gerçekten paralel başlat (create_task olmadan to_thread sıralı çalışır)
    tasks = {key: asyncio.create_task(coro) for key, coro in coros.items()}

    # Run all in parallel, collect results
    results = {}
    for key, task in tasks.items():
        try:
            results[key] = await task
        except Exception as e:
            log.warning(f"[orchestrator] {key} arama hatasi: {e}")
            results[key] = []

    log.info(f"[orchestrator] intent={intent} ders={ders} speed={speed_mode} "
             f"pdfs={len(results.get('pdfs',[]))} "
             f"brain={len(results.get('brain',[]))} questions={len(results.get('questions',[]))} "
             f"anki={len(results.get('anki',[]))}")

    return results
