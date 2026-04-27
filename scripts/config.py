"""
DUS Mentörü — Paylaşılan Konfigürasyon ve Sabitler
"""
import os
import sys

# .env dosyasını yükle
try:
    from dotenv import load_dotenv
    # Scripts klasöründe olduğumuz için bir üst dizine bakıyoruz
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Root'ta çalıştırılıyorsa direkt .env bak
        load_dotenv(".env")
except ImportError:
    pass

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# ─── API Anahtarları ───
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
OPENAI_API_KEY   = os.environ.get("OPENAI_API_KEY", "")

# ─── Supabase ───
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vblndoyjmkgaeuihydyd.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ─── Pinecone ───
MYBRAIN_HOST = "https://mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io"
MYPPDFS_HOST = "https://myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io"

# ─── Modeller ───
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
]

# ─── Chunking Parametreleri ───
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ─── Dizinler ───
BASE_DUS_PATH = r"C:\Users\FURKAN\Desktop\DUS"
