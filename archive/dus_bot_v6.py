import sys
import os
import time
import uuid
import telebot
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai
from google.genai import types
from google.api_core import exceptions as gapi_exceptions
from openai import OpenAI
from supabase import create_client, Client
from embedding_utils import embedder

# Load environment variables
load_dotenv()

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# --- CONFIGURATION ---
# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# Model fallback zinciri
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
]

# Index host adresleri
MYBRAIN_HOST   = "https://mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io"
MYPPDFS_HOST   = "https://myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io"

# --- INITIALIZATION ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Global session memory
session_history = {}

# Host üzerinden bağlan
memory_index = pc.Index(host=MYBRAIN_HOST)
pato_index   = pc.Index(host=MYPPDFS_HOST)


# ─── PINECONE ARAMA VE RERANK YARDIMCISI ────────────────────────────────────────

def _pinecone_search(index, namespace: str, query: str, top_k: int = 15) -> list[dict]:
    """
    1. Llama ile vektörleştir.
    2. Pinecone'dan top_k aday çek.
    3. Reranker ile en alakalı olanları en üste al.
    """
    try:
        # 1. Embed query (Llama)
        query_vec = embedder.embed_text(query, is_query=True)

        # 2. Vector Search (Initial candidates)
        results = index.query(
            namespace=namespace,
            vector=query_vec,
            top_k=top_k,
            include_metadata=True
        )
        
        matches = results.get("matches", [])
        if not matches:
            return []

        # 3. Rerank (Pinecone Inference API)
        # BGE-Reranker-v2-m3 kullanıyoruz
        documents = [m["metadata"]["text"] for m in matches]
        
        try:
            rerank_res = pc.inference.rerank(
                model="bge-reranker-v2-m3",
                query=query,
                documents=documents,
                top_n=5, # En iyi 5 sonucu döndür
                parameters={"return_documents": True}
            )
            
            # Reranked results'ları orijinal metadata ile birleştir
            final_results = []
            for rank_item in rerank_res.data:
                # Orijinal indeksi bulup metadata'yı alıyoruz
                idx = rank_item.index
                final_results.append(matches[idx]["metadata"])
            
            return final_results
        except Exception as re:
            print(f"[WARN] Rerank hatası ({re}), orijinal sıralama kullanılıyor.")
            return [m["metadata"] for m in matches[:5]]

    except Exception as e:
        print(f"[ERROR] _pinecone_search hatası: {e}")
        return []


# --- TOOL FUNCTIONS ---

def search_memory(query: str) -> str:
    """Furkan'ın DUS ilerleyişi, notları ve hafızası hakkında arama yapar."""
    print(f"[TOOL] search_memory: {query}")
    try:
        results = _pinecone_search(memory_index, "dus-data", query)
        if not results:
            return "Hafızada bu konuyla ilgili bir bilgi bulunamadı."
        
        context = "--- Furkan'ın Hafıza Kayıtları ---\n"
        for meta in results:
            source = meta.get("source", "Bilinmiyor")
            text   = meta.get("text", "")
            context += f"\n[Kaynak: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Hafıza arama hatası: {str(e)}"


def search_pathology(query: str) -> str:
    """Patoloji ders notları içindeki klinik bilgileri sorgular."""
    print(f"[TOOL] search_pathology: {query}")
    try:
        results = _pinecone_search(pato_index, "patoloji", query)
        if not results:
            return "Patoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        
        context = "--- Patoloji Notlarından Bilgiler ---\n"
        for meta in results:
            source = meta.get("source", "Bilinmiyor")
            text   = meta.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Patoloji arama hatası: {str(e)}"


def search_radiology(query: str) -> str:
    """Radyoloji ders notları içindeki klinik bilgileri sorgular."""
    print(f"[TOOL] search_radiology: {query}")
    try:
        results = _pinecone_search(pato_index, "radyoloji", query)
        if not results:
            return "Radyoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        
        context = "--- Radyoloji Notlarından Bilgiler ---\n"
        for meta in results:
            source = meta.get("source", "Bilinmiyor")
            text   = meta.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Radyoloji arama hatası: {str(e)}"


def search_endodontics(query: str) -> str:
    """Endodonti ders notları (klinik bilgi) içinde arama yapar."""
    print(f"[TOOL] search_endodontics: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "endodonti", query, top_k=5)
        if not fields_list:
            return "Endodonti notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Endodonti Notlarından Bilgiler ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Endodonti arama hatası: {str(e)}"


def search_prosthodontics(query: str) -> str:
    """Protez ders notları (klinik bilgi) içinde arama yapar."""
    print(f"[TOOL] search_prosthodontics: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "protez", query, top_k=5)
        if not fields_list:
            return "Protez notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Protez Notlarından Bilgiler ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Protez arama hatası: {str(e)}"


def search_histology(query: str) -> str:
    """Histoloji ve Embriyoloji ders notları (klinik bilgi) içinde arama yapar."""
    print(f"[TOOL] search_histology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "histoloji", query, top_k=5)
        if not fields_list:
            return "Histoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Histoloji Notlarından Bilgiler ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Histoloji arama hatası: {str(e)}"


def search_physiology(query: str) -> str:
    """Fizyoloji ders notları (klinik bilgi) içinde arama yapar."""
    print(f"[TOOL] search_physiology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "fizyoloji", query, top_k=5)
        if not fields_list:
            return "Fizyoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Fizyoloji Notlarından Bilgiler ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Fizyoloji arama hatası: {str(e)}"


def search_periodontology(query: str) -> str:
    """Periodontoloji ders notları (klinik bilgi) içinde arama yapar."""
    print(f"[TOOL] search_periodontology: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "periodontoloji", query, top_k=5)
        if not fields_list:
            return "Periodontoloji notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Periodontoloji Notlarından Bilgiler ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Periodontoloji arama hatası: {str(e)}"


def search_surgery(query: str) -> str:
    """Ağız Diş ve Çene Cerrahisi ders notları (klinik bilgi) içinde arama yapar."""
    print(f"[TOOL] search_surgery: {query}")
    try:
        fields_list = _pinecone_search(pato_index, "cerrahi", query, top_k=5)
        if not fields_list:
            return "Cerrahi notlarında bu konuyla ilgili bir bilgi bulunamadı."
        context = "--- Ağız Diş ve Çene Cerrahisi Notlarından Bilgiler ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Dosya: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Cerrahi arama hatası: {str(e)}"


def search_project_memory(query: str) -> str:
    """AI asistan proje belleği ve karar logları (claude_memory) içinde arama yapar."""
    print(f"[TOOL] search_project_memory: {query}")
    try:
        fields_list = _pinecone_search(memory_index, "claude_memory", query, top_k=5)
        if not fields_list:
            return "Proje belleğinde bu konuyla ilgili bir kayıt bulunamadı."
        context = "--- Proje Belleğinden Kayıtlar ---\n"
        for fields in fields_list:
            source = fields.get("source", "Bilinmiyor")
            text   = fields.get("text", "")
            context += f"\n[Kayıt: {source}]\n{text}\n"
        return context
    except Exception as e:
        return f"Proje belleği arama hatası: {str(e)}"


def search_questions(query: str, lesson: str = None) -> str:
    """DUSBANKASI soru bankasından benzer soruları ve açıklamalarını getirir."""
    print(f"[TOOL] search_questions: {query} (Lesson: {lesson})")
    try:
        # 1. Embed query with OpenAI
        response = openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding

        # 2. Call Supabase RPC
        # match_questions_semantic(query_embedding, match_threshold, match_count, p_lesson)
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": 0.5,
            "match_count": 3,
            "p_lesson": lesson if lesson else "Patoloji" # Default to Patoloji
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
                output += f"✅ Cevap: {d['correct_answer']}\n📖 Açıklama: {d['explanation']}\n"
                output += f"(Ünite: {d['unit']})\n-------------------\n"
        
        return output
    except Exception as e:
        return f"Soru arama hatası: {str(e)}"


def remember_fact(fact_text: str) -> str:
    """Önemli bir bilgiyi Furkan'ın uzun vadeli hafızasına kaydeder."""
    print(f"[TOOL] remember_fact: {fact_text}")
    try:
        memory_index.upsert(
            namespace="dus-data",
            vectors=[{
                "id": f"fact-{uuid.uuid4().hex}",
                "values": embedder.embed_text(fact_text),
                "metadata": {
                    "text": fact_text,
                    "source": "Telegram Bot Chat",
                    "type": "learned_fact",
                }
            }]
        )
        return "Bilgi başarıyla hafızaya kaydedildi."
    except Exception as e:
        return f"Kayıt hatası: {str(e)}"


def save_chat_history(chat_id: str) -> str:
    """Konuşma geçmişini hem 'vektörlenecek' klasörüne hem de Pinecone'a kaydeder."""
    print(f"[TOOL] save_chat_history: {chat_id}")
    chat_id_int = int(chat_id) if isinstance(chat_id, str) and chat_id.isdigit() else chat_id
    history = session_history.get(chat_id_int, [])
    
    if not history:
        return "Kaydedilecek bir konuşma geçmişi bulunamadı."
    
    # Geçmişi metne çevir
    chat_text = f"# Chat History - {chat_id}\nDate: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    for msg in history:
        role = msg.role
        content = ""
        for part in msg.parts:
            if part.text:
                content += part.text
        chat_text += f"### {role.upper()}\n{content}\n\n"
    
    # 1. LOKAL KAYIT (Zorunlu)
    try:
        os.makedirs("vektörlenecek", exist_ok=True)
        filename = f"vektörlenecek/chat_{chat_id}_{int(time.time())}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(chat_text)
        local_status = f"Lokal kayıt başarılı ({filename})."
    except Exception as e:
        local_status = f"Lokal kayıt hatası: {e}"

    # 2. PINECONE KAYIT (Opsiyonel/Kota Bağımlı)
    try:
        memory_index.upsert(
            namespace="chathistory",
            vectors=[{
                "id": f"chat-{chat_id}-{int(time.time())}",
                "values": embedder.embed_text(chat_text),
                "metadata": {
                    "text": chat_text,
                    "source": f"Chat Session {chat_id}",
                    "type": "chathistory",
                    "date": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }]
        )
        pinecone_status = "Pinecone kaydı başarılı."
    except Exception as e:
        pinecone_status = f"Pinecone kaydı (Kota vb. sebeple) yapılamadı: {e}"

    return f"{local_status} | {pinecone_status}"


# --- GEMINI TOOLS DEFINITION ---
gemini_tools = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="search_memory",
            description="Furkan'ın DUS ilerleyişi ve notları hakkında arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Arama sorgusu")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_pathology",
            description="Patoloji ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_radiology",
            description="Radyoloji ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_endodontics",
            description="Endodonti ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_project_memory",
            description="AI asistan proje belleği ve karar logları içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Proje ile ilgili sorgu")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_questions",
            description="DUSBANKASI soru bankasından benzer soruları ve açıklamalarını getirir.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(type="STRING", description="Soru konusu"),
                    "lesson": types.Schema(type="STRING", description="Ders adı (Patoloji, Histoloji, Fizyoloji, Endodonti, Periodontoloji, Protez, Radyoloji)")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_prosthodontics",
            description="Protez ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_histology",
            description="Histoloji ve Embriyoloji ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_physiology",
            description="Fizyoloji ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_periodontology",
            description="Periodontoloji ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_surgery",
            description="Ağız Diş ve Çene Cerrahisi ders notları (klinik bilgi) içinde arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Klinik konu veya terim")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="remember_fact",
            description="Önemli bir bilgiyi Furkan'ın uzun vadeli hafızasına kaydeder.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"fact_text": types.Schema(type="STRING", description="Kaydedilecek bilgi")},
                required=["fact_text"]
            )
        ),
        types.FunctionDeclaration(
            name="save_chat_history",
            description="Mevcut konuşma geçmişini 'chathistory' namespace'ine kaydeder.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"chat_id": types.Schema(type="STRING", description="Mevcut sohbet ID'si (genellikle sistem tarafından sağlanır)")},
                required=["chat_id"]
            )
        ),
    ])
]

SYSTEM_PROMPT = (
    "Sen Furkan'ın 'DUS Mentörü' adında zeki bir asistanısın. "
    "Furkan DUS (Diş Hekimliğinde Uzmanlık Sınavı) öğrencisidir. "
    "Onun ilerleyişini, notlarını ve günlüklerini Pinecone hafızasından sorgulayabilirsin. "
    "Eğer bir konu hakkında 'soru' veya 'örnek' isterse 'search_questions' kullan. "
    "Ders adını biliyorsan 'lesson' parametresine ekle (varsayılan Patoloji). "
    "Dilin samimi, profesyonel, motive edici ve Türkçe olsun."
)


def call_tool(name: str, args: dict) -> str:
    if name == "search_memory":
        return search_memory(args["query"])
    elif name == "search_pathology":
        return search_pathology(args["query"])
    elif name == "search_radiology":
        return search_radiology(args["query"])
    elif name == "search_endodontics":
        return search_endodontics(args["query"])
    elif name == "search_project_memory":
        return search_project_memory(args["query"])
    elif name == "search_questions":
        return search_questions(args["query"], args.get("lesson"))
    elif name == "search_prosthodontics":
        return search_prosthodontics(args["query"])
    elif name == "search_histology":
        return search_histology(args["query"])
    elif name == "search_physiology":
        return search_physiology(args["query"])
    elif name == "search_periodontology":
        return search_periodontology(args["query"])
    elif name == "search_surgery":
        return search_surgery(args["query"])
    elif name == "remember_fact":
        return remember_fact(args["fact_text"])
    elif name == "save_chat_history":
        return save_chat_history(args["chat_id"])
    return "Bilinmeyen araç."


# --- GEMINI API ÇAĞRISI ---

def generate_with_retry(messages, retries=5):
    last_error = None
    for model_name in GEMINI_MODELS:
        for attempt in range(retries):
            try:
                print(f"[API] model={model_name} attempt={attempt + 1}")
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
                    break  # Bu model yok, sonrakine geç
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    break  # Kota doldu, sonraki modele geç
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    wait = 10 * (2 ** attempt)  # 503 geçici yoğunluk: daha uzun bekle
                    print(f"[API] 503 geçici yoğunluk, {wait}s bekleniyor...")
                    time.sleep(wait)
                    continue
                if attempt < retries - 1:
                    time.sleep(5 * (2 ** attempt))
                else:
                    break
    raise RuntimeError(f"MODEL_BUSY: {str(last_error)[:200]}")


# --- AGENT LOOP ---

def chat_with_agent(chat_id: int, user_message: str) -> str:
    # Get or initialize history
    if chat_id not in session_history:
        session_history[chat_id] = []
    
    messages = session_history[chat_id]
    messages.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    
    # Keep history within reasonable limits (last 20 turns)
    if len(messages) > 40:
        messages = messages[-40:]
        session_history[chat_id] = messages

    for round_num in range(8):
        response = generate_with_retry(messages)
        if not response.candidates: return "Hata: Yanıt alınamadı."
        
        candidate = response.candidates[0]
        messages.append(candidate.content)
        
        parts = candidate.content.parts or []
        tool_results = []
        
        has_tool_call = False
        for part in parts:
            if part.function_call:
                fc = part.function_call
                print(f"[AGENT] Tool: {fc.name} | args={fc.args}")
                
                # chat_id'yi otomatik inject et (eğer araç bekliyorsa)
                args = dict(fc.args)
                if fc.name == "save_chat_history":
                    args["chat_id"] = str(chat_id)
                
                result = call_tool(fc.name, args)
                tool_results.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result}
                    )
                ))
                has_tool_call = True
 
         if has_tool_call:
             messages.append(types.Content(role="tool", parts=tool_results))
         else:
             for part in reversed(parts):
                 if part.text: return part.text
             return "Anladım."
 
     return "İşlem çok uzadı, lütfen daha spesifik sorar mısın?"


# --- BOT HANDLERS ---

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message,
        "Selam Furkan! Ben senin DUS Mentörün. 🦷\n\n"
        "✅ Hafızandaki notlara erişebilirim.\n"
        "✅ Klinik notları (Patoloji, Radyoloji, Endodonti, Protez, Histoloji, Fizyoloji, Periodontoloji, Cerrahi) sorgulayabilirim.\n"
        "✅ DUSBANKASI'ndan soru ve açıklama getirebilirim!\n\n"
        "Örn: 'Periodontal cerrahi sonrası bakım nasıl olmalı?' veya 'Hücre hasarı soruları getir'"
    )

@bot.message_handler(commands=["stats"])
def show_stats(message):
    try:
        sm = memory_index.describe_index_stats()
        sp = pato_index.describe_index_stats()
        sq = supabase.table("questions").select("id", count="exact").limit(1).execute()
        
        text = "📊 **Sistem Durumu**\n\n"
        text += f"🧠 **Hafıza (mybrain):** {sm.get('total_vector_count', '?')} kayıt\n"
        text += f"   - dus-data: {sm['namespaces'].get('dus-data', {}).get('record_count', 0)}\n"
        text += f"   - claude_memory: {sm['namespaces'].get('claude_memory', {}).get('record_count', 0)}\n\n"
        text += f"🔬 **Ders Notları (myppdfs):** {sp.get('total_vector_count', '?')} kayıt\n"
        text += f"   - patoloji: {sp['namespaces'].get('patoloji', {}).get('record_count', 0)}\n"
        text += f"   - endodonti: {sp['namespaces'].get('endodonti', {}).get('record_count', 0)}\n"
        text += f"   - radyoloji: {sp['namespaces'].get('radyoloji', {}).get('record_count', 0)}\n"
        text += f"   - protez: {sp['namespaces'].get('protez', {}).get('record_count', 0)}\n"
        text += f"   - histoloji: {sp['namespaces'].get('histoloji', {}).get('record_count', 0)}\n"
        text += f"   - fizyoloji: {sp['namespaces'].get('fizyoloji', {}).get('record_count', 0)}\n"
        text += f"   - periodontoloji: {sp['namespaces'].get('periodontoloji', {}).get('record_count', 0)}\n"
        text += f"   - cerrahi: {sp['namespaces'].get('cerrahi', {}).get('record_count', 0)}\n\n"
        text += f"❓ **Soru Bankası:** {sq.count} soru\n"
        text += f"🤖 **Model:** {GEMINI_MODELS[0]}\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"İstatistik hatası: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        print(f"[MSG] {message.chat.id}: {message.text}")
        bot.send_chat_action(message.chat.id, "typing")
        response_text = chat_with_agent(message.chat.id, message.text)
        bot.reply_to(message, response_text)
    except Exception as e:
        print(f"[ERROR] {e}")
        bot.reply_to(message, f"Bir hata oluştu: {str(e)[:200]}")

if __name__ == "__main__":
    print("[*] DUS Mentörü Botu (v2 - Supabase Entegre) başlatılıyor...")
    bot.infinity_polling()
