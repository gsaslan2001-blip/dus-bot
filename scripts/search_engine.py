import os
import sys
import asyncio
from pinecone import Pinecone
from supabase import create_client, Client
from embedding_utils import get_embedder, get_local_embedder

# Config import
sys.path.append(os.path.dirname(__file__))
from config import (
    PINECONE_API_KEY, 
    MYBRAIN_HOST, 
    MYPPDFS_HOST, 
    SUPABASE_URL, 
    SUPABASE_KEY
)

# Clients
pc = Pinecone(api_key=PINECONE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5):
    """
    High-Precision RAG: Embedding -> Vector Search -> Reranking (Synchronous)
    """
    host = MYBRAIN_HOST if index_name == "mybrain" else MYPPDFS_HOST
    index = pc.Index(host=host)
    
    current_embedder = get_local_embedder()
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
            model="bge-reranker-v2-m3",
            query=query,
            documents=[m["metadata"]["text"] for m in res["matches"]],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [d.document.text for d in rank_res.data]
    except Exception as e:
        print(f"[search] Rerank hatası (fallback'e geçiliyor): {e}")
        return [m["metadata"]["text"] for m in res["matches"][:rerank_top_n]]

async def async_pinecone_search_ns(index, query_vec, namespace, top_k=15):
    """
    Single namespace search for asyncio.gather.
    """
    effective_namespace = namespace if namespace else "__default__"
    # Pinecone sync calls run in threads to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: index.query(
            namespace=effective_namespace,
            vector=query_vec,
            top_k=top_k,
            include_metadata=True
        )
    )

async def search_multi_ns(query: str, index_name: str, namespaces: list[str], top_k: int = 15, rerank_top_n: int = 5):
    """
    Parallel multi-namespace search followed by global reranking.
    """
    host = MYBRAIN_HOST if index_name == "mybrain" else MYPPDFS_HOST
    index = pc.Index(host=host)
    
    current_embedder = get_local_embedder()
    vector = current_embedder.embed_text(query, is_query=True)
    
    # Parallelize queries
    tasks = [async_pinecone_search_ns(index, vector, ns, top_k) for ns in namespaces]
    results = await asyncio.gather(*tasks)
    
    # Flatten matches and combine
    all_matches = []
    for res in results:
        all_matches.extend(res.get("matches", []))
    
    if not all_matches:
        return []

    # Sort all combined matches by score (initial filtering)
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = all_matches[:top_k * 2] # Take more for reranking
    
    try:
        rank_res = pc.inference.rerank(
            model="bge-reranker-v2-m3",
            query=query,
            documents=[m["metadata"]["text"] for m in top_candidates if "text" in m.get("metadata", {})],
            top_n=rerank_top_n,
            return_documents=True
        )
        return [d.document.text for d in rank_res.data]
    except Exception as e:
        print(f"[search] Multi-ns Rerank hatası: {e}")
        return [m["metadata"]["text"] for m in top_candidates[:rerank_top_n]]

async def async_pinecone_search(query: str, index_name: str, namespace: str, top_k: int = 15, rerank_top_n: int = 5):
    """
    Asynchronous version of pinecone_search for parallel independent queries.
    """
    host = MYBRAIN_HOST if index_name == "mybrain" else MYPPDFS_HOST
    index = pc.Index(host=host)
    
    current_embedder = get_local_embedder()
    
    # Run embedding in executor (CPU/GPU intensive)
    loop = asyncio.get_event_loop()
    vector = await loop.run_in_executor(None, lambda: current_embedder.embed_text(query, is_query=True))
    
    res = await async_pinecone_search_ns(index, vector, namespace, top_k)
    
    matches = res.get("matches", [])
    if not matches:
        return []
    
    try:
        # Rerank is also an API call
        rank_res = await loop.run_in_executor(
            None,
            lambda: pc.inference.rerank(
                model="bge-reranker-v2-m3",
                query=query,
                documents=[m["metadata"]["text"] for m in matches if "text" in m.get("metadata", {})],
                top_n=rerank_top_n,
                return_documents=True
            )
        )
        return [d.document.text for d in rank_res.data]
    except Exception as e:
        print(f"[search] Async Rerank hatası: {e}")
        return [m["metadata"]["text"] for m in matches[:rerank_top_n]]

def search_questions(query: str, lesson: str = None, limit: int = 5):
    """
    Supabase (DUSBANK) üzerinden semantik soru araması yapar.
    """
    # Not: Soru bankası OpenAI ada-002 (1536-dim) kullanıyor olabilir, 
    # projenin geri kalanında OpenAI anahtarı gereklidir.
    try:
        # Bu fonksiyon dus_bot içindeki 'match_questions_semantic' RPC'sini çağırır
        # Şimdilik basitleştirilmiş hali:
        from openai import OpenAI
        oa_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        vec = oa_client.embeddings.create(
            input=[query], 
            model="text-embedding-3-small"
        ).data[0].embedding
        
        params = {"query_embedding": vec, "match_threshold": 0.5, "match_count": limit}
        if lesson:
            params["filter_lesson"] = lesson
            
        res = supabase.rpc("match_questions_semantic", params).execute()
        return res.data
    except Exception as e:
        print(f"[search] Soru bankası hatası: {e}")
        return []
