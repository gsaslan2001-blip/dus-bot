"""Tests for bot/tools/search_tools.py — tool dispatcher and individual tools."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestExecuteTool:
    @pytest.fixture(autouse=True)
    def patch_search_fns(self, monkeypatch):
        self.mock_pinecone = MagicMock(return_value=[])
        self.mock_multi_ns = MagicMock(return_value=[])
        self.mock_questions = MagicMock(return_value=[])
        monkeypatch.setattr("bot.tools.search_tools.pinecone_search", self.mock_pinecone)
        monkeypatch.setattr("bot.tools.search_tools.search_multi_ns", self.mock_multi_ns)
        monkeypatch.setattr("bot.tools.search_tools.search_questions", self.mock_questions)

    async def test_dispatch_search_ders_notlari(self):
        from bot.tools.search_tools import execute_tool
        result = await execute_tool("search_ders_notlari", {"query": "patoloji", "ders": "patoloji"})
        assert isinstance(result, str)
        self.mock_pinecone.assert_called_once()

    async def test_dispatch_search_hafiza(self):
        from bot.tools.search_tools import execute_tool
        result = await execute_tool("search_hafiza", {"query": "ilerleme"})
        assert isinstance(result, str)
        self.mock_multi_ns.assert_called_once()

    async def test_dispatch_search_soru_bankasi(self):
        from bot.tools.search_tools import execute_tool
        result = await execute_tool("search_soru_bankasi", {"query": "patoloji sorusu", "ders": "patoloji"})
        assert isinstance(result, str)
        self.mock_questions.assert_called_once()

    async def test_dispatch_search_anki(self):
        from bot.tools.search_tools import execute_tool
        result = await execute_tool("search_anki", {"query": "protez", "ders": "protez"})
        assert isinstance(result, str)
        self.mock_pinecone.assert_called_once()

    async def test_unknown_tool_returns_error_message(self):
        from bot.tools.search_tools import execute_tool
        result = await execute_tool("bilinmeyen_arac", {"query": "test"})
        assert "Bilinmeyen" in result or "bilinmeyen" in result.lower()

    async def test_search_ders_notlari_with_results(self):
        from bot.tools.search_tools import execute_tool
        self.mock_pinecone.return_value = [{"text": "patoloji içeriği", "score": 0.9}]
        result = await execute_tool("search_ders_notlari", {"query": "tümör", "ders": "patoloji"})
        assert "patoloji içeriği" in result
        assert "PATOLOJI" in result

    async def test_search_ders_notlari_no_results_message(self):
        from bot.tools.search_tools import execute_tool
        self.mock_pinecone.return_value = []
        result = await execute_tool("search_ders_notlari", {"query": "bilinmeyen", "ders": "patoloji"})
        assert "bulunamadi" in result.lower() or "bulunamadı" in result.lower()

    async def test_search_hafiza_with_results(self):
        from bot.tools.search_tools import execute_tool
        self.mock_multi_ns.return_value = [{"text": "geçmiş çalışma kaydı"}]
        result = await execute_tool("search_hafiza", {"query": "ne çalıştım"})
        assert "geçmiş çalışma kaydı" in result

    async def test_search_soru_bankasi_no_ders(self):
        from bot.tools.search_tools import execute_tool
        result = await execute_tool("search_soru_bankasi", {"query": "genel soru"})
        assert isinstance(result, str)
        self.mock_questions.assert_called_once()

    async def test_search_soru_bankasi_formats_question(self):
        from bot.tools.search_tools import execute_tool
        self.mock_questions.return_value = [
            {"question_text": "Soru metni", "correct_answer": "A", "explanation": "Açıklama"}
        ]
        result = await execute_tool("search_soru_bankasi", {"query": "soru"})
        assert "Soru metni" in result
        assert "Açıklama" in result

    async def test_search_anki_no_results_message(self):
        from bot.tools.search_tools import execute_tool
        self.mock_pinecone.return_value = []
        result = await execute_tool("search_anki", {"query": "bilinmeyen", "ders": "radyoloji"})
        assert "bulunamadi" in result.lower() or "bulunamadı" in result.lower()

    async def test_search_error_returns_error_string(self):
        from bot.tools.search_tools import execute_tool
        self.mock_pinecone.side_effect = Exception("Pinecone bağlantı hatası")
        result = await execute_tool("search_ders_notlari", {"query": "test", "ders": "patoloji"})
        assert "hata" in result.lower()


class TestToolDefinitions:
    def test_all_four_tools_defined(self):
        from bot.tools.search_tools import TOOL_DEFINITIONS
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        assert names == {"search_ders_notlari", "search_hafiza", "search_soru_bankasi", "search_anki"}

    def test_all_tools_have_required_fields(self):
        from bot.tools.search_tools import TOOL_DEFINITIONS
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
