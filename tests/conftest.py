"""
Shared fixtures. Must set env vars before any bot.* modules are imported,
since bot.settings reads them at module level with os.environ[...].
"""
import os
import sys

# Inject required env vars before any import of bot.* or scripts.*
_ENV_DEFAULTS = {
    "TELEGRAM_TOKEN": "test_telegram_token",
    "DEEPSEEK_API_KEY": "test_deepseek_key",
    "PINECONE_API_KEY": "test_pinecone_key",
    "ALLOWED_CHAT_IDS": "123456,789012",
    "OPENAI_API_KEY": "test_openai_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test_supabase_key",
}
for k, v in _ENV_DEFAULTS.items():
    os.environ.setdefault(k, v)

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Pre-import bot package so patch() targets resolve correctly
import bot.deps  # noqa: F401


@pytest.fixture(autouse=True)
def mock_bot_deps(monkeypatch):
    """
    Patch all external clients in bot.deps so tests never hit live APIs.
    Applied automatically to every test via autouse=True.
    """
    mock_pc = MagicMock()
    mock_deepseek = MagicMock()
    mock_openai = MagicMock()
    mock_supabase = MagicMock()
    mock_index = MagicMock()
    mock_pc.Index.return_value = mock_index

    import bot.deps as deps
    monkeypatch.setattr(deps, "pc", mock_pc)
    monkeypatch.setattr(deps, "mybrain_idx", mock_index)
    monkeypatch.setattr(deps, "myppdfs_idx", mock_index)
    monkeypatch.setattr(deps, "anki_idx", mock_index)
    monkeypatch.setattr(deps, "deepseek", mock_deepseek)
    monkeypatch.setattr(deps, "openai_client", mock_openai)
    monkeypatch.setattr(deps, "supabase", mock_supabase)

    yield {
        "pc": mock_pc,
        "deepseek": mock_deepseek,
        "openai": mock_openai,
        "supabase": mock_supabase,
        "index": mock_index,
    }
