import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional

from pinecone import Pinecone
from supabase import create_client, Client
from openai import OpenAI

from embedding_utils import get_local_embedder
from dotenv import load_dotenv

# --- Configuration & Logging ---
load_dotenv() # .env dosyasından değişkenleri yükle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_RERANKER_MODEL = "bge-reranker-v2-m3"

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "")
MYPPDFS_HOST = os.environ.get("MYPPDFS_HOST", "")

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
    
    # Güvenli fallback (Kullanıcı eski davranışı istiyor olabilir, hardcode'u izole ettik)
    host = MYBRAIN_HOST or "mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io"
    if index_name != "mybrain":
        host = MYPPDFS_HOST or "myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io"
        
    return pc.Index(host=host)

def _get_question_embedding(query: str) -> List[float]:
    """Supabase soru araması için sorguyu vektörler."""
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

    if index_name in ["mybrain", "myppdfs"]:
        current_embedder = get_local_embedder(provider="local")
    else:
        current_embedder = get_local_embedder(provider="openai")
        
    vector = current_embedder.embed_text(query, is_query=True)
    
    effective_namespace = namespace if namespace else "__default__"
    
    res = index.query(
        namespace=effective_namespace,
        vector=vector,
        top_k=top_k,
        include_metadata=True
    )
    
    if not res.get("matches"):
        return []
    
    try:
        rank_res = pc.inference.rerank(
            model=DEFAULT_RERANKER_MODEL,
            query=query,
            documents=[m.get("metadata", {}).get("text", "") for m in res["matches"] if m.get("metadata", {}).get("text")],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [d.document.text for d in rank_res.data]
    except Exception as e:
        logger.warning(f"[search] Rerank hatası (fallback'e geçiliyor): {e}")
        return [m.get("metadata", {}).get("text", "") for m in res["matches"][:rerank_top_n]]

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
    """Parallel multi-namespace search followed by global reranking."""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Multi-ns arama yapılamıyor.")
        return []

    if index_name in ["mybrain", "myppdfs"]:
        current_embedder = get_local_embedder(provider="local")
    else:
        current_embedder = get_local_embedder(provider="openai")
        
    vector = current_embedder.embed_text(query, is_query=True)
    
    tasks = [async_pinecone_search_ns(index, vector, ns, top_k) for ns in namespaces]
    results = await asyncio.gather(*tasks)
    
    all_matches = []
    for res in results:
        all_matches.extend(res.get("matches", []))
    
    if not all_matches:
        return []

    all_matches.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = all_matches[:top_k * 2]
    
    try:
        rank_res = pc.inference.rerank(
            model=DEFAULT_RERANKER_MODEL,
            query=query,
            documents=[m["metadata"]["text"] for m in top_candidates if "text" in m.get("metadata", {})],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [d.document.text for d in rank_res.data]
    except Exception as e:
        logger.warning(f"[search] Multi-ns Rerank hatası: {e}")
        return [m.get("metadata", {}).get("text", "") for m in top_candidates[:rerank_top_n]]

async def async_pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5) -> List[str]:
    """Asynchronous version of pinecone_search for parallel independent queries."""
    try:
        index = _get_pinecone_index(index_name)
    except ValueError as e:
        logger.error(f"[search] {e} Async arama yapılamıyor.")
        return []
    
    if index_name in ["mybrain", "myppdfs"]:
        current_embedder = get_local_embedder(provider="local")
    else:
        current_embedder = get_local_embedder(provider="openai")
    
    vector = await asyncio.to_thread(current_embedder.embed_text, query, is_query=True)
    
    res = await async_pinecone_search_ns(index, vector, namespace, top_k)
    matches = res.get("matches", [])
    
    if not matches:
        return []
    
    try:
        rank_res = await asyncio.to_thread(
            pc.inference.rerank,
            model=DEFAULT_RERANKER_MODEL,
            query=query,
            documents=[m["metadata"]["text"] for m in matches if "text" in m.get("metadata", {})],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [d.document.text for d in rank_res.data]
    except Exception as e:
        logger.warning(f"[search] Async Rerank hatası: {e}")
        return [m.get("metadata", {}).get("text", "") for m in matches[:rerank_top_n]]


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
