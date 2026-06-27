import asyncio
import logging
from scripts.search_engine import pinecone_search, search_questions

log = logging.getLogger(__name__)

# Tool definitions in OpenAI function-calling format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_ders_notlari",
            "description": "DUS ders notlarinda (myppdfs) arama yapar. Patoloji, Radyoloji, Endodonti, "
                           "Protez, Histoloji, Fizyoloji, Periodontoloji, Cerrahi, Farmakoloji, "
                           "Pedodonti, Restoratif gibi branslarda kullanilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Arama sorgusu (Turkce)"},
                    "ders": {
                        "type": "string",
                        "enum": ["patoloji", "radyoloji", "endodonti", "protez", "histoloji",
                                 "fizyoloji", "periodontoloji", "cerrahi", "farmakoloji",
                                 "pedodonti", "ortodonti", "restoratif"],
                        "description": "Ders/brans adi"
                    }
                },
                "required": ["query", "ders"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_soru_bankasi",
            "description": "~20.000 DUS sorusu iceren bankada (Supabase) arama yapar. "
                           "Benzer sorulari ve aciklamalarini getirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Arama sorgusu"},
                    "ders": {
                        "type": "string",
                        "description": "Ders adi (opsiyonel): Patoloji, Histoloji, Fizyoloji, vb."
                    }
                },
                "required": ["query"]
            }
        }
    }
]


async def execute_tool(name: str, args: dict) -> str:
    """Tool execution dispatcher."""
    if name == "search_ders_notlari":
        return await _search_ders_notlari(args["query"], args["ders"])
    elif name == "search_soru_bankasi":
        return await _search_soru_bankasi(args["query"], args.get("ders"))
    else:
        return f"Bilinmeyen arac: {name}"


async def _search_ders_notlari(query: str, ders: str) -> str:
    log.info(f"[tool] search_ders_notlari: ders={ders} query={query[:60]}")
    try:
        results = await asyncio.to_thread(pinecone_search, query, "myppdfs", ders, 15, 5)
        if not results:
            return f"'{ders}' notlarinda bu konuyla ilgili bir sey bulunamadi."
        out = f"--- {ders.upper()} Ders Notlari ---\n"
        for i, r in enumerate(results):
            if isinstance(r, dict):
                out += f"\n[{i+1}] (benzerlik: {r.get('score', '?')})\n{r.get('text', '')}\n"
            else:
                out += f"\n[{i+1}]\n{r}\n"
        return out
    except Exception as e:
        return f"Ders notlari arama hatasi: {e}"


async def _search_soru_bankasi(query: str, ders: str | None) -> str:
    log.info(f"[tool] search_soru_bankasi: query={query[:60]}")
    try:
        # Pure semantic search — ders filtresi yok, reranker konu alaka düzeyini belirler
        results = await asyncio.to_thread(search_questions, query, None, 5)
        if not results:
            return "Soru bankasinda eslesen soru bulunamadi."
        out = "--- DUS Soru Bankasi ---\n"
        for i, q in enumerate(results):
            out += (f"\n[ Soru {i+1} ]\n"
                    f"{q.get('question_text', q.get('question', ''))}\n"
                    f"Cevap: {q.get('correct_answer', '?')}\n"
                    f"Aciklama: {q.get('explanation', q.get('explanation', 'Yok'))}\n")
        return out
    except Exception as e:
        return f"Soru bankasi arama hatasi: {e}"
