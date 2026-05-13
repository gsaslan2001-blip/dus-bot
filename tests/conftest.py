"""
Global test configuration.

Must run before any bot.* import so that:
  1. Required environment variables are present (bot.settings uses os.environ[...])
  2. Heavy external clients (Pinecone, Supabase, DeepSeek) are replaced with
     lightweight mocks before their initialisation code executes.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# ─── Environment variables ────────────────────────────────────────────────────
os.environ.setdefault("TELEGRAM_TOKEN", "test_telegram_token")
os.environ.setdefault("DEEPSEEK_API_KEY", "test_deepseek_key")
os.environ.setdefault("PINECONE_API_KEY", "test_pinecone_key")
os.environ.setdefault("ALLOWED_CHAT_IDS", "123456")
os.environ.setdefault("MYBRAIN_HOST", "test-mybrain.pinecone.io")
os.environ.setdefault("MYPPDFS_HOST", "test-myppdfs.pinecone.io")
os.environ.setdefault("ANKI_HOST", "test-anki.pinecone.io")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test_supabase_key")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")

# ─── Mock Pinecone ────────────────────────────────────────────────────────────
mock_pinecone_index = MagicMock()
mock_pinecone_index.describe_index_stats.return_value = {
    "total_vector_count": 0, "namespaces": {}
}
mock_pinecone_mod = MagicMock()
mock_pinecone_mod.Pinecone.return_value.Index.return_value = mock_pinecone_index
sys.modules.setdefault("pinecone", mock_pinecone_mod)

# ─── Mock OpenAI / httpx ─────────────────────────────────────────────────────
sys.modules.setdefault("httpx", MagicMock())

mock_openai_mod = MagicMock()
sys.modules.setdefault("openai", mock_openai_mod)

# ─── Mock Supabase ────────────────────────────────────────────────────────────
sys.modules.setdefault("supabase", MagicMock())

# ─── Mock PyMuPDF ────────────────────────────────────────────────────────────
sys.modules.setdefault("fitz", MagicMock())

# ─── Mock scripts.search_engine ───────────────────────────────────────────────
# orchestrator.py and search_tools.py both import from this module.
mock_search_engine = MagicMock()
mock_search_engine.pinecone_search = MagicMock(return_value=[])
mock_search_engine.search_multi_ns = AsyncMock(return_value=[])
mock_search_engine.search_questions = MagicMock(return_value=[])

# Register as both the bare module and as a scripts sub-module
sys.modules.setdefault("scripts", MagicMock())
sys.modules["scripts.search_engine"] = mock_search_engine
sys.modules["search_engine"] = mock_search_engine  # bare name (scripts/ on sys.path)

# ─── Mock bot.deps ────────────────────────────────────────────────────────────
# bot/__init__.py inserts scripts/ into sys.path; deps.py creates the API clients.
# We replace the whole module so no network calls happen at import time.
mock_deepseek = MagicMock()
mock_deepseek_response = MagicMock()
mock_deepseek_response.choices = [MagicMock(message=MagicMock(content='{"intent": "genel"}'))]
mock_deepseek.chat.completions.create = AsyncMock(return_value=mock_deepseek_response)

mock_deps = MagicMock()
mock_deps.deepseek = mock_deepseek
mock_deps.mybrain_idx = mock_pinecone_index
mock_deps.myppdfs_idx = mock_pinecone_index
mock_deps.anki_idx = mock_pinecone_index
mock_deps.supabase = MagicMock()

sys.modules["bot.deps"] = mock_deps

# ─── Mock bot.prompts ─────────────────────────────────────────────────────────
mock_prompts = MagicMock()
mock_prompts.system_prompt.SYSTEM_PROMPT = "system prompt"
mock_prompts.system_prompt.SYSTEM_PROMPT_FAST = "fast system prompt"
sys.modules.setdefault("bot.prompts", mock_prompts)
sys.modules.setdefault("bot.prompts.system_prompt", MagicMock(
    SYSTEM_PROMPT="system prompt",
    SYSTEM_PROMPT_FAST="fast system prompt",
))
