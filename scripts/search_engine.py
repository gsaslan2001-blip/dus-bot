import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional

from pinecone import Pinecone
from supabase import create_client, Client
from openai import OpenAI

try:
    from scripts.embedding_utils import get_embedder  # Railway: WORKDIR=/app
except ImportError:
    from embedding_utils import get_embedder  # Direkt scripts/ içinden çalıştırma
from dotenv import load_dotenv

# --- Configuration & Logging ---
load_dotenv() # .env dosyasından değişkenleri yükle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_RERANKER_MODEL = os.environ.get("RERANKER_MODEL", "bge-reranker-v2-m3")
SEARCH_TIMEOUT = float(os.environ.get("SEARCH_TIMEOUT", "15.0"))  # saniye — aşırıya kaçan sorguları kes
RERANK_TIMEOUT = float(os.environ.get("RERANK_TIMEOUT", "10.0"))
EMBED_TIMEOUT = float(os.environ.get("EMBED_TIMEOUT", "8.0"))

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "")
MYPPDFS_HOST = os.environ.get("MYPPDFS_HOST", "")
ANKI_HOST = os.environ.get("ANKI_HOST", "")
DUSBANKASI_HOST = os.environ.get("DUSBANKASI_HOST", "dusbankasi-0crkhvy.svc.aped-4627-b74a.pinecone.io")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# --- Clients ---
pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
oa_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# --- Timeout Wrapper ---
async def _with_timeout(coro, timeout: float, label: str = "search"):
    """Coroutine'i timeout ile çalıştır, aşımda boş liste döner."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"[timeout] {label} {timeout}s sınırını aştı — boş dönüyor")
        return []
    except Exception as e:
        logger.warning(f"[{label}] hata: {e}")
        return []


# --- Helpers ---
def _get_pinecone_index(index_name: str):
    """Pinecone indeksini ismine göre güvenli bir şekilde döndürür."""
    if not pc:
        raise ValueError("Pinecone istemcisi başlatılamadı.")
    
    # Güvenli host eşleştirme
    if index_name == "mybrain":
        host = MYBRAIN_HOST or "mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io"
    elif index_name == "anki":
        host = ANKI_HOST or "anki-0crkhvy.svc.aped-4627-b74a.pinecone.io"
    elif index_name == "dusbankasi":
        host = DUSBANKASI_HOST
    else:
        host = MYPPDFS_HOST or "myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io"
        
    return pc.Index(host=host)

def _get_question_embedding(query: str) -> List[float]:
    """DUS Soru Bankası sorgusu için vektörleme (OpenAI text-embedding-3-small, 1536-dim)."""
    # NOT: dusbankasi indeksi OpenAI 3-small 1536-dim mimarisindedir.
    # myppdfs/mybrain E5 1024-dim; anki OpenAI 3-large 3072-dim kullanır.
    if not oa_client:
        raise ValueError("OpenAI istemcisi başlatılamadı.")
    response = oa_client.embeddings.create(
        input=[query], 
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


# --- Pinecone Search Functions ---
def pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5, rerank_enabled: bool = True) -> List[Dict[str, Any]]:
    """High-Precision RAG: Embedding -> Vector Search -> Reranking (Synchronous)"""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Arama yapılamıyor.")
        return []

    effective_namespace = namespace if namespace else "__default__"

    # Integrated Inference & Reranking (HIZLI & KOTAYI AZ HARCAR)
    try:
        search_kwargs = dict(
            namespace=effective_namespace,
            query={"inputs": {"text": query}, "top_k": top_k},
            fields=["text", "source", "file", "page", "chunk_index", "title"],
        )
        if rerank_enabled:
            search_kwargs["rerank"] = {
                "model": DEFAULT_RERANKER_MODEL,
                "top_n": rerank_top_n,
                "rank_fields": ["text"],
            }
        res = index.search(**search_kwargs)

        if res and res.get("result", {}).get("hits"):
            return [
                {
                    "text": hit["fields"].get("text", ""),
                    "score": hit["_score"],
                    "id": hit.get("_id", ""),
                    "source": hit["fields"].get("source"),
                    "file": hit["fields"].get("file"),
                    "page": hit["fields"].get("page"),
                    "chunk_index": hit["fields"].get("chunk_index"),
                    "title": hit["fields"].get("title"),
                }
                for hit in res["result"]["hits"]
            ]
        return []

    except Exception as e:
        logger.warning(f"[search] Integrated Inference/Search hatası, fallback'e geçiliyor: {e}")
        # Fallback: Pinecone Inference API veya OpenAI vektörleme (YEREL MODEL YOK)
        if index_name in ["mybrain", "myppdfs"]:
            current_embedder = get_embedder(provider="pinecone")
        elif index_name == "anki":
            current_embedder = get_embedder(provider="openai", dimension=3072)
        else:
            current_embedder = get_embedder(provider="openai", dimension=1536)

        vector = current_embedder.embed_text(query, is_query=True)
        res = index.query(
            namespace=effective_namespace,
            vector=vector,
            top_k=top_k,
            include_metadata=True
        )
        matches = res.get("matches", [])
        if not matches:
            return []

        if not rerank_enabled:
            return [
                {
                    "text": m.get("metadata", {}).get("text", ""),
                    "score": m.get("score"),
                    "id": m.get("id", ""),
                    "source": m.get("metadata", {}).get("source"),
                    "file": m.get("metadata", {}).get("file"),
                    "page": m.get("metadata", {}).get("page"),
                    "chunk_index": m.get("metadata", {}).get("chunk_index"),
                    "title": m.get("metadata", {}).get("title"),
                }
                for m in matches[:rerank_top_n]
            ]

        try:
            rank_res = pc.inference.rerank(
                model=DEFAULT_RERANKER_MODEL,
                query=query,
                documents=[m.get("metadata", {}).get("text", "") for m in matches if m.get("metadata", {}).get("text")],
                top_n=rerank_top_n,
                return_documents=True
            )
            return [
                {
                    "text": d.document.text,
                    "score": d.score,
                    "id": matches[d.index].get("id", "") if d.index is not None and d.index < len(matches) else "",
                    "source": matches[d.index].get("metadata", {}).get("source") if d.index is not None and d.index < len(matches) else None,
                    "file": matches[d.index].get("metadata", {}).get("file") if d.index is not None and d.index < len(matches) else None,
                }
                for d in rank_res.data
            ]
        except Exception as re:
            logger.warning(f"[search] Standart Rerank hatası: {re}")
            return [
                {
                    "text": m.get("metadata", {}).get("text", ""),
                    "score": m.get("score"),
                    "id": m.get("id", ""),
                    "source": m.get("metadata", {}).get("source"),
                    "file": m.get("metadata", {}).get("file"),
                }
                for m in matches[:rerank_top_n]
            ]

async def search_multi_ns(query: str, index_name: str, namespaces: List[str], top_k: int = 15, rerank_top_n: int = 5, rerank_enabled: bool = True) -> List[Dict[str, Any]]:
    """Parallel multi-namespace search followed by global reranking — timeout korumalı."""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Multi-ns arama yapılamıyor.")
        return []

    async def _single_ns_search(ns):
        try:
            # Her namespace için bağımsız Integrated Search (Hızlı ve Ucuz)
            res = await asyncio.to_thread(
                index.search,
                namespace=ns,
                query={"inputs": {"text": query}, "top_k": top_k},
                fields=["text", "source", "file", "page", "chunk_index", "title"]
            )
            return res.get("result", {}).get("hits", [])
        except Exception as e:
            logger.warning(f"[search] NS {ns} için integrated search hatası: {e}")
            return []

    tasks = [_single_ns_search(ns) for ns in namespaces]
    results = await asyncio.gather(*tasks)
    
    all_hits = []
    for hits in results:
        all_hits.extend(hits)
    
    if not all_hits:
        return []

    # Skorlara göre sırala ve global rerank yap
    all_hits.sort(key=lambda x: x["_score"], reverse=True)
    top_candidates = all_hits[:top_k * 2]

    if not rerank_enabled:
        return [
            {
                "text": h.get("fields", {}).get("text", ""),
                "score": h.get("_score"),
                "id": h.get("_id", ""),
                "source": h.get("fields", {}).get("source"),
                "file": h.get("fields", {}).get("file"),
            }
            for h in top_candidates[:rerank_top_n]
        ]

    try:
        rank_res = await asyncio.to_thread(
            pc.inference.rerank,
            model=DEFAULT_RERANKER_MODEL,
            query=query,
            documents=[h["fields"]["text"] for h in top_candidates if "text" in h.get("fields", {})],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [
            {
                "text": d.document.text,
                "score": d.score,
                "id": top_candidates[d.index].get("_id", "") if d.index is not None and d.index < len(top_candidates) else "",
                "source": top_candidates[d.index].get("fields", {}).get("source") if d.index is not None and d.index < len(top_candidates) else None,
            }
            for d in rank_res.data
        ]
    except Exception as e:
        logger.warning(f"[search] Multi-ns Global Rerank hatası: {e}")
        return [
            {
                "text": h.get("fields", {}).get("text", ""),
                "score": h.get("_score"),
                "id": h.get("_id", ""),
                "source": h.get("fields", {}).get("source"),
            }
            for h in top_candidates[:rerank_top_n]
        ]

async def async_pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5) -> List[Dict[str, Any]]:
    """Asynchronous version of pinecone_search using Integrated Inference — timeout korumalı."""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Async arama yapılamıyor.")
        return []

    effective_namespace = namespace if namespace else "__default__"

    async def _do_search():
        try:
            res = await asyncio.to_thread(
                index.search,
                namespace=effective_namespace,
                query={"inputs": {"text": query}, "top_k": top_k},
                rerank={
                    "model": DEFAULT_RERANKER_MODEL,
                    "top_n": rerank_top_n,
                    "rank_fields": ["text"]
                },
                fields=["text", "source", "file", "page", "chunk_index", "title"]
            )
            if res and res.get("result", {}).get("hits"):
                return [{"text": hit["fields"]["text"], "score": hit["_score"]} for hit in res["result"]["hits"]]
            return []
        except Exception as e:
            logger.warning(f"[search] Async Integrated Search hatası, fallback'e geçiliyor: {e}")
            return await asyncio.to_thread(pinecone_search, query, index_name, namespace, top_k, rerank_top_n)

    return await _with_timeout(_do_search(), SEARCH_TIMEOUT, f"async_search:{index_name}/{effective_namespace}")


# --- Supabase Search Functions ---
async def search_anki_multi_ns(
    query: str, namespaces: List[str], top_k: int = 10,
    rerank_top_n: int = 5, rerank_enabled: bool = True
) -> List[Dict[str, Any]]:
    """Anki indeksi için multi-namespace arama (OpenAI 3072-dim — integrated embed yok).
    Embed işlemi bir kez yapılır, tüm namespace'ler paralel sorgulanır."""
    if not oa_client:
        logger.error("[anki] OpenAI istemcisi yok. OPENAI_API_KEY gerekli.")
        return []

    try:
        vec_resp = await asyncio.to_thread(
            oa_client.embeddings.create,
            model="text-embedding-3-large",
            input=[query],
            dimensions=3072,
        )
        embedding = vec_resp.data[0].embedding
    except Exception as e:
        logger.error(f"[anki] Embedding hatası: {e}")
        return []

    try:
        index = _get_pinecone_index("anki")
    except ValueError as e:
        logger.error(f"[anki] {e}")
        return []

    async def _query_ns(ns: str):
        try:
            res = await asyncio.to_thread(
                index.query,
                namespace=ns,
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
            )
            return [(ns, m) for m in (res.get("matches") or [])]
        except Exception as e:
            logger.warning(f"[anki] NS {ns} sorgu hatası: {e}")
            return []

    all_ns_results = await asyncio.gather(*[_query_ns(ns) for ns in namespaces])
    all_matches = [item for ns_result in all_ns_results for item in ns_result]

    if not all_matches:
        return []

    all_matches.sort(key=lambda x: x[1].get("score", 0), reverse=True)
    top_matches = all_matches[: top_k * 2]

    docs = [m.get("metadata", {}).get("text", "") for _, m in top_matches]
    docs = [d for d in docs if d]

    if not docs:
        return []

    if not rerank_enabled:
        return [
            {"text": m.get("metadata", {}).get("text", ""), "score": m.get("score")}
            for _, m in top_matches[:rerank_top_n]
        ]

    try:
        rank_res = await asyncio.to_thread(
            pc.inference.rerank,
            model=DEFAULT_RERANKER_MODEL,
            query=query,
            documents=docs,
            top_n=rerank_top_n,
            return_documents=True,
        )
        return [{"text": d.document.text, "score": d.score} for d in rank_res.data]
    except Exception as e:
        logger.warning(f"[anki] Rerank hatası: {e}")
        return [
            {"text": m.get("metadata", {}).get("text", ""), "score": m.get("score")}
            for _, m in top_matches[:rerank_top_n]
        ]


def search_questions(query: str, lesson: str = None, limit: int = 5, rerank_enabled: bool = True) -> List[Dict[str, Any]]:
    """Pinecone (dusbankasi) semantik soru araması — pure vector search + rerank.

    lesson parametresi artık kullanılmıyor: keyword filtreleme yerine vektör benzerliği
    ve reranker konu alaka düzeyini belirler. 16072 soru arasında en iyi eşleşme döner.
    """
    if not pc:
        logger.error("[search] Pinecone istemcisi eksik. Arama yapılamıyor.")
        return []

    try:
        # Step 1: Embed query (OpenAI text-embedding-3-small, 1536-dim)
        vec = _get_question_embedding(query)

        # Step 2: Full-bank semantic search — no lesson filter
        index = pc.Index(host=DUSBANKASI_HOST)
        top_k = max(limit * 4, 20)

        res = index.query(vector=vec, top_k=top_k, include_metadata=True)
        matches = res.get("matches", [])

        if not matches:
            return []

        # Step 3: Rerank the candidates
        # Prepare documents for reranker
        documents = []
        for m in matches:
            meta = m.get("metadata", {})
            q_text = meta.get("question", meta.get("text", ""))
            documents.append(q_text)

        if not rerank_enabled:
            return [
                {
                    "id": m.get("id"),
                    "question": m.get("metadata", {}).get("question", m.get("metadata", {}).get("text", "")),
                    "option_a": m.get("metadata", {}).get("option_a", ""),
                    "option_b": m.get("metadata", {}).get("option_b", ""),
                    "option_c": m.get("metadata", {}).get("option_c", ""),
                    "option_d": m.get("metadata", {}).get("option_d", ""),
                    "option_e": m.get("metadata", {}).get("option_e", ""),
                    "correct_answer": m.get("metadata", {}).get("correct_answer", ""),
                    "explanation": m.get("metadata", {}).get("explanation", ""),
                    "lesson": m.get("metadata", {}).get("lesson", ""),
                    "score": m.get("score"),
                }
                for m in matches[:limit]
            ]

        try:
            rank_res = pc.inference.rerank(
                model=DEFAULT_RERANKER_MODEL,
                query=query,
                documents=documents,
                top_n=limit,
                return_documents=True
            )

            # Map reranked results back to original matches via text matching
            # NOTE: d.index Pinecone reranker'da her zaman populate edilmeyebilir
            final_results = []
            for d in rank_res.data:
                reranked_text = d.document.text if hasattr(d.document, 'text') else str(d.document)
                # Find original match by text content
                orig_match = None
                for m in matches:
                    meta = m.get("metadata", {})
                    q_text = meta.get("question", meta.get("text", ""))
                    if q_text == reranked_text:
                        orig_match = m
                        break
                # Fallback: use score-based search if text matching fails
                if orig_match is None:
                    # Try by index if available
                    idx = getattr(d, 'index', None)
                    if idx is not None and 0 <= idx < len(matches):
                        orig_match = matches[idx]
                    else:
                        # Last resort: find by partial text match
                        for m in matches:
                            meta = m.get("metadata", {})
                            q_text = meta.get("question", meta.get("text", ""))
                            if reranked_text[:50] in q_text or q_text[:50] in reranked_text:
                                orig_match = m
                                break
                if orig_match is None:
                    continue
                meta = orig_match.get("metadata", {})
                final_results.append({
                    "id": orig_match.get("id"),
                    "question": meta.get("question", meta.get("text", "")),
                    "option_a": meta.get("option_a", ""),
                    "option_b": meta.get("option_b", ""),
                    "option_c": meta.get("option_c", ""),
                    "option_d": meta.get("option_d", ""),
                    "option_e": meta.get("option_e", ""),
                    "correct_answer": meta.get("correct_answer", ""),
                    "explanation": meta.get("explanation", ""),
                    "lesson": meta.get("lesson", ""),
                    "score": d.score
                })
            return final_results

        except Exception as re:
            logger.warning(f"[search] Question Rerank hatası: {re}")
            # Fallback to original vector search order
            results = []
            for match in matches[:limit]:
                meta = match.get("metadata", {})
                results.append({
                    "id": match.get("id"),
                    "question": meta.get("question", meta.get("text", "")),
                    "option_a": meta.get("option_a", ""),
                    "option_b": meta.get("option_b", ""),
                    "option_c": meta.get("option_c", ""),
                    "option_d": meta.get("option_d", ""),
                    "option_e": meta.get("option_e", ""),
                    "correct_answer": meta.get("correct_answer", ""),
                    "explanation": meta.get("explanation", ""),
                    "lesson": meta.get("lesson", ""),
                    "score": match.get("score")
                })
            return results

    except Exception as e:
        logger.error(f"[search] Pinecone soru bankası hatası: {e}")
        return []

async def async_search_questions(query: str, lesson: str = None, limit: int = 5, rerank_enabled: bool = True) -> List[Dict[str, Any]]:
    """Async Pinecone-direct semantik soru araması (dusbankasi, OpenAI 1536-dim)."""
    return await asyncio.to_thread(search_questions, query, lesson, limit, rerank_enabled)


async def async_search_questions_supabase_legacy(query: str, lesson: str = None, limit: int = 5) -> List[Dict[str, Any]]:
    """[LEGACY] Supabase RPC üzerinden semantik soru araması.
    NOT: Yeni kod için search_questions() kullanın (Pinecone direct, 1536-dim).
    Bu fonksiyon eski Supabase RPC path'ini korur — yalnızca karşılaştırma/geçiş amaçlıdır."""
    if not supabase:
        logger.error("[search] Supabase istemcisi eksik. Arama yapılamıyor.")
        return []

    try:
        vec = await asyncio.to_thread(_get_question_embedding, query)
        params = {
            "query_embedding": vec, 
            "match_threshold": 0.5, 
            "match_count": limit,
            "p_lesson": lesson if lesson else ""
        }
            
        res = await asyncio.to_thread(
            lambda: supabase.rpc("match_questions_semantic", params).execute()
        )
        return res.data
    except Exception as e:
        logger.error(f"[search] Async Soru bankası hatası: {e}")
        return []

# --- CLI Entrypoint ---
def main():
    import argparse
    import json

    # Windows UTF-8 Fix
    if sys.stdout.encoding != 'utf-8':
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="DUS Mentörü Arama Motoru CLI")
    parser.add_argument("query", help="Arama sorgusu")
    parser.add_argument("--index", default="myppdfs", help="Pinecone indeksi (myppdfs veya mybrain)")
    parser.add_argument("--ns", nargs="+", help="Namespace(ler). Boşlukla ayırın.")
    parser.add_argument("--top_k", type=int, default=15, help="Pinecone'dan çekilecek aday sayısı")
    parser.add_argument("--top_n", type=int, default=5, help="Rerank sonrası dönecek sonuç sayısı")
    parser.add_argument("--json", action="store_true", help="Çıktıyı JSON formatında ver")
    parser.add_argument("--questions", action="store_true", help="Supabase soru bankasında ara")
    parser.add_argument("--lesson", help="Ders filtresi (Sadece --questions ile)")

    args = parser.parse_args()

    if args.questions:
        results = search_questions(args.query, lesson=args.lesson, limit=args.top_n)
        if args.json:
            print(json.dumps(results, ensure_ascii=False))
        else:
            for i, r in enumerate(results):
                q_text = r.get('question', '')
                options = f"A) {r.get('option_a', '')}\nB) {r.get('option_b', '')}\nC) {r.get('option_c', '')}\nD) {r.get('option_d', '')}\nE) {r.get('option_e', '')}"
                correct = r.get('correct_answer', '')
                expl = r.get('explanation', '')
                print(f"\n--- SORU {i+1} ---\n{q_text}\n{options}\n\nCEVAP: {correct}\nAÇIKLAMA: {expl}\n")
    else:
        if args.ns and len(args.ns) > 1:
            results = asyncio.run(search_multi_ns(args.query, args.index, args.ns, args.top_k, args.top_n))
        else:
            ns = args.ns[0] if args.ns else None
            results = pinecone_search(args.query, args.index, ns, args.top_k, args.top_n)

        if args.json:
            print(json.dumps(results, ensure_ascii=False))
        else:
            for i, r in enumerate(results):
                text = r.get("text", str(r)) if isinstance(r, dict) else str(r)
                score = r.get("score") if isinstance(r, dict) else None
                score_str = f" (score: {score:.4f})" if score is not None else ""
                print(f"\n--- SONUÇ {i+1}{score_str} ---\n{text}\n--- SONUÇ SONU ---")

if __name__ == "__main__":
    main()
