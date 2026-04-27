import os
import sys
import telebot
from pinecone import Pinecone
import uuid
from flask import Flask, request
from google import genai
from google.genai import types
import time

# Windows encoding fix
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8772695118:AAFLUY5s2cqz9MlwQklXQBFFtEYVX6aKNIU"
GEMINI_API_KEY = "AIzaSyCu7bh_PQp3Es7bkFccqkpwFWQ2dUy72rA"
PINECONE_API_KEY = "pcsk_57q66M_WwyxH5mHedvLaJtZnRsNCb1S2BbMCoiL2ytwid6ycamgHgmY3ZKt9Sd7oVFEny"

# --- INITIALIZATION ---
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
gemini = genai.Client(api_key=GEMINI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("mybrain")

# --- TOOL FUNCTIONS ---
def search_memory(query: str) -> str:
    """Furkan'ın DUS ilerleyişi, notları ve hafızası hakkında arama yapar."""
    try:
        results = index.search(
            namespace='dus-data',
            query={"top_k": 5, "inputs": {'text': query}},
            fields=["text", "source"]
        )
        hits = results.get("result", {}).get("hits", [])
        if not hits: return "Hafızada bu konuyla ilgili bir bilgi bulunamadı."
        context = ""
        for hit in hits:
            fields = hit.get("fields", {})
            context += f"\n[Kaynak: {fields.get('source', 'Bilinmiyor')}]\n{fields.get('text', '')}\n"
        return context
    except Exception as e:
        return f"Arama hatası: {str(e)}"

def remember_fact(fact_text: str) -> str:
    """Önemli bir bilgiyi Furkan'ın uzun vadeli hafızasına kaydeder."""
    try:
        index.upsert_records(
            namespace='dus-data',
            records=[{
                "id": f"fact-{uuid.uuid4().hex}",
                "text": fact_text,
                "source": "Telegram Bot Chat",
                "type": "learned_fact"
            }]
        )
        return "Bilgi başarıyla hafızaya kaydedildi."
    except Exception as e:
        return f"Kayıt hatası: {str(e)}"

# --- GEMINI TOOLS DEFINITION ---
gemini_tools = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="search_memory",
            description="Furkan'ın DUS ilerleyişi, notları ve hafızası hakkında Pinecone'da arama yapar.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Arama sorgusu")},
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
        )
    ])
]

SYSTEM_PROMPT = (
    "Sen Furkan'ın 'DUS Mentorü' adında zeki bir asistanısın. "
    "Soruları yanıtlarken önce 'search_memory' ile hafızaya bak. "
    "Dilin samimi, profesyonel, motive edici ve Türkçe olsun."
)

def chat_with_agent(user_message: str) -> str:
    messages = [types.Content(role="user", parts=[types.Part(text=user_message)])]
    for _ in range(5):
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=gemini_tools,
                temperature=0.7,
            )
        )
        candidate = response.candidates[0]
        part = candidate.content.parts[0]
        if hasattr(part, 'text') and part.text: return part.text
        if hasattr(part, 'function_call') and part.function_call:
            fc = part.function_call
            if fc.name == "search_memory": res = search_memory(fc.args["query"])
            else: res = remember_fact(fc.args["fact_text"])
            messages.append(candidate.content)
            messages.append(types.Content(role="tool", parts=[types.Part(function_response=types.FunctionResponse(name=fc.name, response={"result": res}))]))
        else: return response.text or "Hata oluştu."
    return "Limit aşıldı."

app = Flask(__name__)

@app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    return "DUS Mentor Bot is alive!", 200

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Selam Furkan! Ben senin DUS Mentorünüm. Hafızandaki tüm verilere erişimim var. Nereden devam edelim?")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        response_text = chat_with_agent(message.text)
        bot.reply_to(message, response_text)
    except Exception as e:
        bot.reply_to(message, f"Hata: {str(e)[:200]}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
