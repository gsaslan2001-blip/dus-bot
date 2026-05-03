import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional

from pinecone import Pinecone
from supabase import create_client, Client
from openai import OpenAI

from embedding_utils import get_embedder
from dotenv import load_dotenv

# --- Configuration & Logging ---
load_dotenv() # .env dosyasından değişkenleri yükle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_RERANKER_MODEL = "bge-reranker-v2-m3"

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "")
MYPPDFS_HOST = os.environ.get("MYPPDFS_HOST", "")
ANKI_HOST = os.environ.get("ANKI_HOST", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# --- Clients ---
pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
oa_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
    else:
        host = MYPPDFS_HOST or "myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io"
        
    return pc.Index(host=host)

def _get_question_embedding(query: str) -> List[float]:
    """Supabase soru araması için sorguyu vektörler (DUS Soru Bankası - OpenAI-Ada tabanlı)."""
    # NOT: Soru bankası (Supabase) geçmişten gelen bir karar ile 1536-dim OpenAI-Ada 
    # mimarisindedir. Bu bir istisnadır. Diğer tüm süreçler E5'e çekilmiştir.
    if not oa_client:
        raise ValueError("OpenAI istemcisi başlatılamadı.")
    response = oa_client.embeddings.create(
        input=[query], 
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


# --- Pinecone Search Functions ---
def pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5) -> List[str]:
    """High-Precision RAG: Embedding -> Vector Search -> Reranking (Synchronous)"""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Arama yapılamıyor.")
        return []

    effective_namespace = namespace if namespace else "__default__"

    # Integrated Inference & Reranking (HIZLI & KOTAYI AZ HARCAR)
    try:
        res = index.search(
            namespace=effective_namespace,
            query={
                "inputs": {"text": query},
                "top_k": top_k
            },
            rerank={
                "model": DEFAULT_RERANKER_MODEL,
                "top_n": rerank_top_n,
                "rank_fields": ["text"]
            },
            fields=["text"]
        )
        
        if res and res.get("result", {}).get("hits"):
            return [{"text": hit["fields"]["text"], "score": hit["_score"]} for hit in res["result"]["hits"]]
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
            
        try:
            rank_res = pc.inference.rerank(
                model=DEFAULT_RERANKER_MODEL,
                query=query,
                documents=[m.get("metadata", {}).get("text", "") for m in matches if m.get("metadata", {}).get("text")],
                top_n=rerank_top_n,
                return_documents=True
            )
            return [{"text": d.document.text, "score": d.score} for d in rank_res.data]
        except Exception as re:
            logger.warning(f"[search] Standart Rerank hatası: {re}")
            return [m.get("metadata", {}).get("text", "") for m in matches[:rerank_top_n]]

async def async_pinecone_search_ns(index, query_vec: List[float], namespace: str, top_k: int = 15):
    """Single namespace search for asyncio.gather."""
    effective_namespace = namespace if namespace else "__default__"
    return await asyncio.to_thread(
        index.query,
        namespace=effective_namespace,
        vector=query_vec,
        top_k=top_k,
        include_metadata=True
    )

async def search_multi_ns(query: str, index_name: str, namespaces: List[str], top_k: int = 15, rerank_top_n: int = 5) -> List[str]:
    """Parallel multi-namespace search followed by global reranking using Integrated Inference."""
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
                fields=["text"]
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
    
    try:
        rank_res = await asyncio.to_thread(
            pc.inference.rerank,
            model=DEFAULT_RERANKER_MODEL,
            query=query,
            documents=[h["fields"]["text"] for h in top_candidates if "text" in h.get("fields", {})],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [{"text": d.document.text, "score": d.score} for d in rank_res.data]
    except Exception as e:
        logger.warning(f"[search] Multi-ns Global Rerank hatası: {e}")
        return [h.get("fields", {}).get("text", "") for h in top_candidates[:rerank_top_n]]

async def async_pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5) -> List[str]:
    """Asynchronous version of pinecone_search using Integrated Inference."""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Async arama yapılamıyor.")
        return []
    
    effective_namespace = namespace if namespace else "__default__"
    
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
            fields=["text"]
        )
        if res and res.get("result", {}).get("hits"):
            return [{"text": hit["fields"]["text"], "score": hit["_score"]} for hit in res["result"]["hits"]]
        return []
    except Exception as e:
        logger.warning(f"[search] Async Integrated Search hatası, fallback'e geçiliyor: {e}")
        # Fallback to sync search logic (which has its own fallback)
        return await asyncio.to_thread(pinecone_search, query, index_name, namespace, top_k, rerank_top_n)


# --- Supabase Search Functions ---
def search_questions(query: str, lesson: str = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Supabase (DUSBANK) üzerinden semantik soru araması yapar."""
    if not supabase:
        logger.error("[search] Supabase istemcisi eksik. Arama yapılamıyor.")
        return []

    try:
        vec = _get_question_embedding(query)
        params = {
            "query_embedding": vec, 
            "match_threshold": 0.5, 
            "match_count": limit,
            "p_lesson": lesson if lesson else "" # Boş string veya None gönder
        }
            
        res = supabase.rpc("match_questions_semantic", params).execute()
        return res.data
    except Exception as e:
        logger.error(f"[search] Soru bankası hatası: {e}")
        return []

async def async_search_questions(query: str, lesson: str = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Supabase (DUSBANK) üzerinden semantik soru araması yapar (Asenkron)."""
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

    args = parser.parse_args()

    if args.questions:
        results = search_questions(args.query, limit=args.top_n)
        if args.json:
            print(json.dumps(results, ensure_ascii=False))
        else:
            for i, r in enumerate(results):
                print(f"\n--- SORU {i+1} ---\n{r.get('question_text', '')}\n")
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
                print(f"\n--- SONUÇ {i+1} ---\n{r}\n--- SONUÇ SONU ---")

if __name__ == "__main__":
    main()
