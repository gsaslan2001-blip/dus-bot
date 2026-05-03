from pinecone import Pinecone
from openai import AsyncOpenAI, OpenAI
from supabase import create_client, Client

from bot.settings import (
    PINECONE_API_KEY, MYBRAIN_HOST, MYPPDFS_HOST, ANKI_HOST,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY,
)

# --- Pinecone Client ---
pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None

# Index instances
def _get_index(host: str):
    if not pc:
        raise RuntimeError("Pinecone client baslatilamadi.")
    return pc.Index(host=host)

mybrain_idx = _get_index(MYBRAIN_HOST) if pc else None
myppdfs_idx = _get_index(MYPPDFS_HOST) if pc else None
anki_idx = _get_index(ANKI_HOST) if pc else None

# --- DeepSeek Client (Async) ---
deepseek = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
) if DEEPSEEK_API_KEY else None

# --- OpenAI Client (Sync — embedding fallback) ---
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- Supabase Client ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
