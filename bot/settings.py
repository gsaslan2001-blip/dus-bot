import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED_CHAT_IDS = set(
    int(x.strip()) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
)

# --- DeepSeek ---
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # V4 Pro flagship

# --- Pinecone ---
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "https://mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io")
MYPPDFS_HOST = os.environ.get("MYPPDFS_HOST", "https://myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io")
ANKI_HOST = os.environ.get("ANKI_HOST", "https://anki-0crkhvy.svc.aped-4627-b74a.pinecone.io")

# --- OpenAI (fallback embedding + anki/dusbankasi) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# --- Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vblndoyjmkgaeuihydyd.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# --- Reranker ---
RERANKER_MODEL = "bge-reranker-v2-m3"

# --- Agent ---
MAX_AGENT_ITERATIONS = 5
CONVERSATION_TTL_SECONDS = 3600  # 1 hour
