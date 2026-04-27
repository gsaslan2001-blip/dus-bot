"""
main.py — DUS Mentörü Telegram Botu
FastAPI + Webhook mimarisi → Cloud Run'da 7/24 çalışır.
Bilgisayarın kapalı olabilir.
"""

import os
import sys
import time
import uuid
import logging
import httpx
from fastapi import FastAPI, Request, Response
from pinecone import Pinecone
from google import genai
from google.genai import types
from openai import OpenAI
from supabase import create_client, Client
from embedding_utils import get_embedder, get_local_embedder

# ─── Merkezi Konfigürasyon ────────────────────────────────────────────────────
from config import (
    TELEGRAM_TOKEN,
    GEMINI_API_KEY,
    PINECONE_API_KEY,
    OPENAI_API_KEY,
    SUPABASE_URL,
    SUPABASE_KEY,
    MYBRAIN_HOST,
    MYPPDFS_HOST,
    GEMINI_MODELS,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

SYSTEM_PROMPT = (
    "Sen Furkan'ın 'DUS Mentörü' adında zeki bir asistanısın. "
    "Furkan DUS (Diş Hekimliğinde Uzmanlık Sınavı) öğrencisidir. "
    "Onun ilerleyişini, notlarını ve günlüklerini Pinecone hafızasından sorgulayabilirsin. "
    "Eğer bir konu hakkında 'soru' veya 'örnek' isterse 'search_questions' kullan. "
    "Ders adını biliyorsan 'lesson' parametresine ekle (varsayılan Patoloji). "
    "Dilin samimi, profesyonel, motive edici ve Türkçe olsun."
)

# ─── Servisler ────────────────────────────────────────────────────────────────
gemini_client  = genai.Client(api_key=GEMINI_API_KEY)
pc             = Pinecone(api_key=PINECONE_API_KEY)
openai_client  = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

memory_index = pc.Index(host=MYBRAIN_HOST)
pato_index   = pc.Index(host=MYPPDFS_HOST)

app = FastAPI()

# ─── Telegram Gönderici ───────────────────────────────────────────────────────
async def send(chat_id: int, text: str, parse_mode: str = "Markdown"):
    MAX = 4000
    parts = [text[i: i + MAX] for i in range(0, len(text), MAX)]
    async with httpx.AsyncClient(timeout=30) as client:
        for part in parts:
            await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": part, "parse_mode": parse_mode},
            )

async def send_action(chat_id: int, action: str = "typing"):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
        )

# ─── Pinecone Arama Yardımcısı ────────────────────────────────────────────────
def _pinecone_search(index, namespace: str, query: str, top_k: int = 5) -> list[dict]:
    try:
        # Get host to determine which embedder to use
        host = index._host
        if MYBRAIN_HOST in host:
            vector = get_embedder().embed_text(query, is_query=True)
        else:
            vector = get_local_embedder().embed_text(query, is_query=True)
        
        # API 2025-04+ protection: replace empty namespace with "__default__"
        effective_namespace = namespace if namespace else "__default__"
        
        results = index.query(
            namespace=effective_namespace,
            vector=vector,
            top_k=15,
            include_metadata=True
        )
        matches = results.get("matches", [])
        if not matches:
            return []
        
        # 2. Aşama: Reranking (Pinecone Inference API)
        try:
            rank_res = pc.inference.rerank(
                model="bge-reranker-v2-m3",
                query=query,
                documents=[m["metadata"]["text"] for m in matches if "text" in m.get("metadata", {})],
                top_n=top_k,
                return_documents=True
            )
            return [{"text": d.document.text, "source": next((m["metadata"].get("source") for m in matches if m["metadata"].get("text") == d.document.text), "?")} for d in rank_res.data]
        except Exception as e:
            log.warning(f"Rerank hatası (fallback): {e}")
            return [m.get("metadata", {}) for m in matches[:top_k]]
    except Exception as e:
        log.error(f"Pinecone arama hatası: {e}")
        raise RuntimeError(f"Pinecone arama hatası: {e}") from e


# ─── Tool Fonksiyonları ───────────────────────────────────────────────────────
def search_memory(query: str) -> str:
    log.info(f"[TOOL] search_memory: {query}")
    try:
        fields_list = _pinecone_search(memory_index, "dus-data", query, top_k=5)
        if not fields_list:
            return "Hafızada bu konuyla ilgili bir bilgi bulunamadı."
        context = ""
        for f in fields_list:
            context += f"\n[Kaynak: {f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Hafıza arama hatası: {e}"


def search_pathology(query: str) -> str:
    log.info(f"[TOOL] search_pathology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "patoloji", query, top_k=5)
        if not fields_list:
            return "Patoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Patoloji Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Patoloji arama hatası: {e}"


def search_radiology(query: str) -> str:
    log.info(f"[TOOL] search_radiology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "radyoloji", query, top_k=5)
        if not fields_list:
            return "Radyoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Radyoloji Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Radyoloji arama hatası: {e}"


def search_endodontics(query: str) -> str:
    log.info(f"[TOOL] search_endodontics: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "endodonti", query, top_k=5)
        if not fields_list:
            return "Endodonti notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Endodonti Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Endodonti arama hatası: {e}"


def search_prosthodontics(query: str) -> str:
    log.info(f"[TOOL] search_prosthodontics: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "protez", query, top_k=5)
        if not fields_list:
            return "Protez notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Protez Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Protez arama hatası: {e}"


def search_histology(query: str) -> str:
    log.info(f"[TOOL] search_histology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "histoloji", query, top_k=5)
        if not fields_list:
            return "Histoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Histoloji Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Histoloji arama hatası: {e}"


def search_physiology(query: str) -> str:
    log.info(f"[TOOL] search_physiology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "fizyoloji", query, top_k=5)
        if not fields_list:
            return "Fizyoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Fizyoloji Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Fizyoloji arama hatası: {e}"


def search_periodontology(query: str) -> str:
    log.info(f"[TOOL] search_periodontology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "periodontoloji", query, top_k=5)
        if not fields_list:
            return "Periodontoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Periodontoloji Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Periodontoloji arama hatası: {e}"


def search_surgery(query: str) -> str:
    log.info(f"[TOOL] search_surgery: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "cerrahi", query, top_k=5)
        if not fields_list:
            return "Ağız Diş ve Çene Cerrahisi notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Ağız Diş ve Çene Cerrahisi Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Cerrahi arama hatası: {e}"


def search_pharmacology(query: str) -> str:
    log.info(f"[TOOL] search_pharmacology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "farmakoloji", query, top_k=5)
        if not fields_list:
            return "Farmakoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Farmakoloji Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Farmakoloji arama hatası: {e}"


def search_pedodontics(query: str) -> str:
    log.info(f"[TOOL] search_pedodontics: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "pedodonti", query, top_k=5)
        if not fields_list:
            return "Pedodonti notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Pedodonti Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Pedodonti arama hatası: {e}"


def search_restorative(query: str) -> str:
    log.info(f"[TOOL] search_restorative: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "restoratif", query, top_k=5)
        if not fields_list:
            return "Restoratif Diş Tedavisi notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Restoratif Diş Tedavisi Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Restoratif arama hatası: {e}"


def search_anatomy(query: str) -> str:
    log.info(f"[TOOL] search_anatomy: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "anatomi", query, top_k=5)
        if not fields_list:
            return "Anatomi notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Anatomi Notlarından ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Anatomi arama hatası: {e}"


def search_project_memory(query: str) -> str:
    log.info(f"[TOOL] search_project_memory: {query}")
    try:
        fields_list = _pinecone_search(memory_index, "claude_memory", query, top_k=5)
        if not fields_list:
            return "Proje belleğinde bu konuyla ilgili bir kayıt bulunamadı."
        context = "--- Proje Belleğinden ---\n"
        for f in fields_list:
            context += f"\n[{f.get('source', '?')}]\n{f.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Proje belleği arama hatası: {e}"


def search_questions(query: str, lesson: str = None) -> str:
    log.info(f"[TOOL] search_questions: {query} (lesson={lesson})")
    try:
        response = openai_client.embeddings.create(
            input=query, model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": 0.5,
            "match_count": 3,
            "p_lesson": lesson if lesson else "Patoloji",
        }
        result = supabase.rpc("match_questions_semantic", rpc_params).execute()
        if not result.data:
            return f"'{lesson or 'Patoloji'}' dersinde bu konuyla ilgili soru bulunamadı."
        output = "--- Bulunan Benzer Sorular ---\n"
        for q in result.data:
            q_id = q.get("id")
            q_details = supabase.table("questions").select("*").eq("id", q_id).single().execute()
            if q_details.data:
                d = q_details.data
                output += f"\nSoru: {d['question']}\nA) {d['option_a']}\nB) {d['option_b']}\nC) {d['option_c']}\nD) {d['option_d']}\nE) {d['option_e']}\n"
                output += f"✅ Cevap: {d['correct_answer']}\n📖 {d['explanation']}\n(Ünite: {d['unit']})\n---\n"
        return output
    except Exception as e:
        return f"Soru arama hatası: {e}"


def remember_fact(fact_text: str) -> str:
    log.info(f"[TOOL] remember_fact: {fact_text[:60]}...")
    try:
        memory_index.upsert_records(
            namespace="dus-data",
            records=[{
                "id": f"fact-{uuid.uuid4().hex}",
                "text": fact_text,
                "source": "Telegram Bot Chat",
                "type": "learned_fact",
            }]
        )
        return "Bilgi başarıyla hafızaya kaydedildi."
    except Exception as e:
        return f"Kayıt hatası: {e}"


# ─── Gemini Tool Tanımları ────────────────────────────────────────────────────
gemini_tools = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="search_memory",
            description="Furkan'ın DUS ilerleyişi ve notları hakkında arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_pathology",
            description="Patoloji ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_radiology",
            description="Radyoloji ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_endodontics",
            description="Endodonti ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_prosthodontics",
            description="Protez ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_histology",
            description="Histoloji ve Embriyoloji ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_physiology",
            description="Fizyoloji ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_periodontology",
            description="Periodontoloji ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_surgery",
            description="Ağız Diş ve Çene Cerrahisi ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_pharmacology",
            description="Farmakoloji ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_pedodontics",
            description="Pedodonti ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_restorative",
            description="Restoratif Diş Tedavisi ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_anatomy",
            description="Anatomi ders notları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_project_memory",
            description="AI asistan proje belleği ve karar logları içinde arama yapar.",
            parameters=types.Schema(type="OBJECT", properties={"query": types.Schema(type="STRING")}, required=["query"])
        ),
        types.FunctionDeclaration(
            name="search_questions",
            description="DUSBANKASI soru bankasından benzer soruları getirir.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(type="STRING"),
                    "lesson": types.Schema(type="STRING", description="Ders adı: Patoloji, Histoloji, Fizyoloji, Endodonti, Periodontoloji, Protez, Radyoloji, Farmakoloji, Pedodonti")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="remember_fact",
            description="Önemli bir bilgiyi Furkan'ın uzun vadeli hafızasına kaydeder.",
            parameters=types.Schema(type="OBJECT", properties={"fact_text": types.Schema(type="STRING")}, required=["fact_text"])
        ),
    ])
]


# ─── Tool Çağırıcı ────────────────────────────────────────────────────────────
def call_tool(name: str, args: dict) -> str:
    dispatch = {
        "search_memory":       lambda a: search_memory(a["query"]),
        "search_pathology":    lambda a: search_pathology(a["query"]),
        "search_radiology":    lambda a: search_radiology(a["query"]),
        "search_endodontics":  lambda a: search_endodontics(a["query"]),
        "search_prosthodontics": lambda a: search_prosthodontics(a["query"]),
        "search_histology":    lambda a: search_histology(a["query"]),
        "search_physiology":   lambda a: search_physiology(a["query"]),
        "search_periodontology": lambda a: search_periodontology(a["query"]),
        "search_surgery":      lambda a: search_surgery(a["query"]),
        "search_pharmacology": lambda a: search_pharmacology(a["query"]),
        "search_pedodontics":  lambda a: search_pedodontics(a["query"]),
        "search_restorative":  lambda a: search_restorative(a["query"]),
        "search_anatomy":      lambda a: search_anatomy(a["query"]),
        "search_project_memory": lambda a: search_project_memory(a["query"]),
        "search_questions":    lambda a: search_questions(a["query"], a.get("lesson")),
        "remember_fact":       lambda a: remember_fact(a["fact_text"]),
    }
    fn = dispatch.get(name)
    return fn(args) if fn else "Bilinmeyen araç."


# ─── Gemini Retry ─────────────────────────────────────────────────────────────
def generate_with_retry(messages, retries=5):
    last_error = None
    for model_name in GEMINI_MODELS:
        for attempt in range(retries):
            try:
                log.info(f"[API] model={model_name} attempt={attempt+1}")
                return gemini_client.models.generate_content(
                    model=model_name,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=gemini_tools,
                        temperature=0.7,
                    )
                )
            except Exception as e:
                last_error = e
                err_str = str(e).upper()
                if "NOT_FOUND" in err_str or "404" in err_str:
                    log.warning(f"[API] 404 NOT_FOUND. Sonraki modele geçiliyor: {model_name}")
                    break
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    log.warning(f"[API] 429 RESOURCE_EXHAUSTED. Sonraki modele geçiliyor: {model_name}")
                    break
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    wait = 10 * (2 ** attempt)
                    log.warning(f"[API] 503, {wait}s bekleniyor... (model: {model_name}, deneme: {attempt+1}/{retries})")
                    time.sleep(wait)
                    continue
                if attempt < retries - 1:
                    time.sleep(3 * (2 ** attempt))
                else:
                    break
    raise RuntimeError(f"MODEL_BUSY: {str(last_error)[:200]}")


# ─── Agent Loop ───────────────────────────────────────────────────────────────
def chat_with_agent(user_message: str) -> str:
    messages = [types.Content(role="user", parts=[types.Part(text=user_message)])]
    for _ in range(8):
        response = generate_with_retry(messages)
        if not response.candidates:
            return "Hata: Yanıt alınamadı."
        candidate = response.candidates[0]
        messages.append(candidate.content)
        parts = candidate.content.parts or []
        tool_results = []
        has_tool_call = False
        for part in parts:
            if part.function_call:
                fc = part.function_call
                log.info(f"[AGENT] Tool={fc.name} args={dict(fc.args)}")
                result = call_tool(fc.name, dict(fc.args))
                tool_results.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name, response={"result": result}
                    )
                ))
                has_tool_call = True
        if has_tool_call:
            messages.append(types.Content(role="tool", parts=tool_results))
        else:
            for part in reversed(parts):
                if part.text:
                    return part.text
            return "Anladım."
    return "İşlem çok uzadı, lütfen daha spesifik sorar mısın?"


# ─── Webhook Endpoint ─────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data    = await request.json()
        message = data.get("message") or data.get("edited_message", {})
        if not message:
            return Response(status_code=200)
        chat_id = message.get("chat", {}).get("id")
        text    = (message.get("text") or "").strip()
        if not chat_id or not text:
            return Response(status_code=200)

        log.info(f"[MSG] chat={chat_id} text={text[:80]}")

        # /start veya /help
        if text.startswith("/start") or text.startswith("/help"):
            await send(
                chat_id,
                "Selam Furkan! Ben senin *DUS Mentörün* 🦷\n\n"
                "✅ Hafızandaki notlara erişebilirim\n"
                "✅ Patoloji, Radyoloji, Endodonti, Protez, Histoloji, Fizyoloji, Periodontoloji, Cerrahi\n"
                "✅ DUSBANKASI'ndan soru ve açıklama getirebilirim\n\n"
                "Örn: _Periodontal cerrahi sonrası bakım nasıl olmalı?_",
            )
            return Response(status_code=200)

        # /stats
        if text.startswith("/stats"):
            try:
                sm = memory_index.describe_index_stats()
                sp = pato_index.describe_index_stats()
                sq = supabase.table("questions").select("id", count="exact").limit(1).execute()
                ns_m = sm.get("namespaces", {})
                ns_p = sp.get("namespaces", {})
                stats_text = (
                    "📊 *Sistem Durumu*\n\n"
                    f"🧠 *mybrain:* {sm.get('total_vector_count','?')} kayıt\n"
                    f"  dus-data: {ns_m.get('dus-data',{}).get('vector_count',0)}\n"
                    f"  claude_memory: {ns_m.get('claude_memory',{}).get('vector_count',0)}\n\n"
                    f"🔬 *myppdfs:* {sp.get('total_vector_count','?')} kayıt\n"
                    f"  patoloji: {ns_p.get('patoloji',{}).get('vector_count',0)}\n"
                    f"  endodonti: {ns_p.get('endodonti',{}).get('vector_count',0)}\n"
                    f"  radyoloji: {ns_p.get('radyoloji',{}).get('vector_count',0)}\n"
                    f"  protez: {ns_p.get('protez',{}).get('vector_count',0)}\n"
                    f"  histoloji: {ns_p.get('histoloji',{}).get('vector_count',0)}\n"
                    f"  fizyoloji: {ns_p.get('fizyoloji',{}).get('vector_count',0)}\n"
                    f"  periodontoloji: {ns_p.get('periodontoloji',{}).get('vector_count',0)}\n"
                    f"  cerrahi: {ns_p.get('cerrahi',{}).get('vector_count',0)}\n"
                    f"  farmakoloji: {ns_p.get('farmakoloji',{}).get('vector_count',0)}\n"
                    f"  pedodonti: {ns_p.get('pedodonti',{}).get('vector_count',0)}\n"
                    f"  restoratif: {ns_p.get('restoratif',{}).get('vector_count',0)}\n"
                    f"  anatomi: {ns_p.get('anatomi',{}).get('vector_count',0)}\n\n"
                    f"❓ *Soru Bankası:* {sq.count} soru\n"
                    f"🤖 *Model:* {GEMINI_MODELS[0]}\n"
                    f"☁️ *Platform:* Cloud Run (7/24)"
                )
                await send(chat_id, stats_text)
            except Exception as e:
                await send(chat_id, f"İstatistik hatası: {e}", parse_mode="")
            return Response(status_code=200)

        # Normal mesaj — düşünüyor bildirimi gönder
        await send_action(chat_id, "typing")

        # Agent loop (senkron — Cloud Run için yeterli)
        response_text = chat_with_agent(text)
        await send(chat_id, response_text)

    except Exception as e:
        log.error(f"Webhook hatası: {e}", exc_info=True)
        try:
            await send(chat_id, f"⚠️ Bir hata oluştu: {str(e)[:150]}", parse_mode="")
        except Exception:
            pass

    return Response(status_code=200)


# ─── Sağlık Kontrolü (Cloud Run zorunlu) ─────────────────────────────────────
@app.get("/")
async def health():
    return {"status": "ok", "bot": "DUS Mentörü", "model": GEMINI_MODELS[0]}
