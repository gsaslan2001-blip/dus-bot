import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
# İki isim de desteklenir (TELEGRAM_TOKEN | TELEGRAM_BOT_TOKEN) — env-isim çakışması crash yapmasın
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_IDS = set(
    int(x.strip()) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
)
# Ayarlanırsa webhook'ta Telegram secret-token doğrulaması aktif olur (sahte POST'lara karşı)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

# --- DeepSeek ---
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = "deepseek-v4-pro"       # V4 Pro: en güçlü model, varsayılan
DEEPSEEK_CHAT = "deepseek-chat"          # V4 Flash: hızlı chat modeli

AVAILABLE_MODELS = {
    "deepseek-v4-pro": "DeepSeek V4 Pro (Güçlü)",
    "deepseek-chat": "DeepSeek V4 Flash (Hızlı)",
}

# --- Pinecone ---
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
MYPPDFS_HOST = os.environ.get("MYPPDFS_HOST", "myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io")
DUSBANKASI_HOST = os.environ.get("DUSBANKASI_HOST", "dusbankasi-0crkhvy.svc.aped-4627-b74a.pinecone.io")

# --- OpenAI (fallback embedding + dusbankasi) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# --- Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vblndoyjmkgaeuihydyd.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# --- Reranker ---
RERANKER_MODEL = "bge-reranker-v2-m3"
AVAILABLE_RERANKERS = {
    "bge-reranker-v2-m3": "BGE Reranker V2 M3 (Hızlı)",
    "cohere-rerank-3.5": "Cohere Rerank 3.5 (Güçlü)",
}

# --- Agent ---
MAX_AGENT_ITERATIONS = 5
CONVERSATION_TTL_SECONDS = 3600  # 1 hour

# --- User Settings Defaults ---
USER_SETTINGS_DEFAULTS = {
    "model": "deepseek-v4-pro",
    "speed_mode": "balanced",      # fast | balanced | comprehensive
    "search_depth": 5,             # rerank top_n: 3-10
    "rerank_enabled": True,
    "agent_iterations": 3,         # max iterations for agent loop
}

SPEED_MODE_CONFIG = {
    "fast": {
        "label": "Hızlı Mod",
        "desc": "Anında yanıt, minimum arama",
        "agent_iterations": 1,
        "search_depth": 3,
        "rerank_enabled": True,
    },
    "balanced": {
        "label": "Dengeli",
        "desc": "Optimal hız ve derinlik",
        "agent_iterations": 3,
        "search_depth": 5,
        "rerank_enabled": True,
    },
    "comprehensive": {
        "label": "Kapsamlı",
        "desc": "En derin arama, tam analiz",
        "agent_iterations": 5,
        "search_depth": 10,
        "rerank_enabled": True,
    },
}
