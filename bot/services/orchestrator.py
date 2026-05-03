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
        "patoloji": ["patoloji", "tümör", "neoplazi", "karsinom", "sarkom", "inflamasyon"],
        "radyoloji": ["radyoloji", "radyografi", "x-ray", "görüntüleme", "radyasyon"],
        "endodonti": ["endodonti", "kanal tedavisi", "pulpa", "kök kanal"],
        "protez": ["protez", "protez", "kuron", "köprü", "implant"],
        "histoloji": ["histoloji", "doku", "epitel", "bağ doku", "embriyoloji"],
        "fizyoloji": ["fizyoloji", "fonksiyon", "sistem", "homeostaz"],
        "periodontoloji": ["periodontoloji", "periodontal", "diş eti", "gingiva"],
        "cerrahi": ["cerrahi", "çekim", "anestezi", "cerrahi"],
        "farmakoloji": ["farmakoloji", "ilaç", "antibiyotik", "analjezik"],
        "pedodonti": ["pedodonti", "çocuk", "süt dişi", "pediatrik"],
        "restoratif": ["restoratif", "dolgu", "kompozit", "amalgam"],
    }
    query_lower = query.lower()
    for ders, keywords in ders_keywords.items():
        for kw in keywords:
            if kw in query_lower:
                return ders
    return None


async def orchestrate_search(query: str, intent: str, forced_index: str | None = None) -> dict:
    """Run parallel searches across all relevant indexes based on intent.

    Args:
        query: Search query string
        intent: Classified intent (ders_calis, soru_sor, cikmis_analiz, hafiza, genel)
        forced_index: Override index from prefix routing (myppdfs, mybrain, anki, or None)
    """
    tasks: dict[str, asyncio.Task] = {}
    ders = _detect_ders(query)

    # --- myppdfs: Always search when ders detected, or for study intents ---
    pdfs_should_search = (
        forced_index == "myppdfs" or
        intent in ("ders_calis", "soru_sor", "cikmis_analiz") or
        (intent == "genel" and ders is not None)  # Fix: ders tespit edilince ara
    )
    if pdfs_should_search:
        namespaces = [ders] if ders and ders in PDFS_NAMESPACES else PDFS_NAMESPACES[:6]
        cross = CROSS_NS_MAP.get(ders, []) if ders else []
        all_ns = list(dict.fromkeys(namespaces + cross))  # dedupe preserving order
        if len(all_ns) > 1:
            tasks["pdfs"] = asyncio.ensure_future(
                search_multi_ns(query, "myppdfs", all_ns, 15, 5)
            )
        else:
            tasks["pdfs"] = asyncio.to_thread(
                pinecone_search, query, "myppdfs", all_ns[0], 15, 5
            )

    # --- mybrain: Search for memory/progress intents, or forced ---
    brain_should_search = (
        forced_index == "mybrain" or
        intent in ("hafiza", "genel")
    )
    if brain_should_search:
        tasks["brain"] = asyncio.ensure_future(
            search_multi_ns(query, "mybrain", BRAIN_NAMESPACES, 10, 5)
        )

    # --- Supabase questions: For study and exam analysis ---
    if intent in ("ders_calis", "soru_sor", "cikmis_analiz"):
        tasks["questions"] = asyncio.to_thread(
            search_questions, query, ders, 5
        )

    # --- anki: When relevant ders or forced ---
    anki_should_search = (
        forced_index == "anki" or
        ders in ("protez", "radyoloji")
    )
    if anki_should_search:
        ns = ders if ders in ("protez", "radyoloji") else "protez"
        tasks["anki"] = asyncio.to_thread(
            pinecone_search, query, "anki", ns, 10, 3
        )

    # Run all in parallel, collect results
    results = {}
    for key, coro in tasks.items():
        try:
            results[key] = await coro
        except Exception as e:
            log.warning(f"[orchestrator] {key} arama hatasi: {e}")
            results[key] = []

    log.info(f"[orchestrator] intent={intent} ders={ders} pdfs={len(results.get('pdfs',[]))} "
             f"brain={len(results.get('brain',[]))} questions={len(results.get('questions',[]))} "
             f"anki={len(results.get('anki',[]))}")

    return results
