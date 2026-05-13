"""
Tests for bot/tools/search_tools.py

Tests cover:
  - execute_tool() dispatch to correct private handler
  - Output formatting for each tool (with mocked search results)
  - Empty-result messaging
  - Error handling (exception → error string returned, not raised)
  - Unknown tool name handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.tools.search_tools import execute_tool

PATCH_PINECONE = "bot.tools.search_tools.pinecone_search"
PATCH_MULTI = "bot.tools.search_tools.search_multi_ns"
PATCH_QUESTIONS = "bot.tools.search_tools.search_questions"


# ─── execute_tool dispatch ────────────────────────────────────────────────────

class TestExecuteToolDispatch:

    async def test_unknown_tool_returns_error_string(self):
        result = await execute_tool("nonexistent_tool", {})
        assert "Bilinmeyen" in result or "bilinmeyen" in result.lower()

    async def test_search_ders_notlari_dispatched(self):
        with patch(PATCH_PINECONE, return_value=[]) as mock_p:
            result = await execute_tool("search_ders_notlari", {"query": "SCC", "ders": "patoloji"})
        assert mock_p.called
        assert isinstance(result, str)

    async def test_search_hafiza_dispatched(self):
        with patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m:
            result = await execute_tool("search_hafiza", {"query": "notlarim"})
        assert mock_m.called
        assert isinstance(result, str)

    async def test_search_soru_bankasi_dispatched(self):
        with patch(PATCH_QUESTIONS, return_value=[]) as mock_q:
            result = await execute_tool("search_soru_bankasi", {"query": "SCC"})
        assert mock_q.called
        assert isinstance(result, str)

    async def test_search_anki_dispatched(self):
        with patch(PATCH_PINECONE, return_value=[]) as mock_p:
            result = await execute_tool("search_anki", {"query": "protez", "ders": "protez"})
        assert mock_p.called
        assert isinstance(result, str)


# ─── search_ders_notlari formatting ──────────────────────────────────────────

class TestSearchDersNotlari:

    async def test_returns_results_with_header(self):
        hits = [{"text": "SCC is a squamous cell carcinoma.", "score": 0.92}]
        with patch(PATCH_PINECONE, return_value=hits):
            result = await execute_tool("search_ders_notlari", {"query": "SCC", "ders": "patoloji"})
        assert "PATOLOJI" in result
        assert "SCC is a squamous cell carcinoma" in result

    async def test_includes_similarity_score(self):
        hits = [{"text": "some text", "score": 0.87}]
        with patch(PATCH_PINECONE, return_value=hits):
            result = await execute_tool("search_ders_notlari", {"query": "x", "ders": "patoloji"})
        assert "0.87" in result

    async def test_empty_results_return_not_found_message(self):
        with patch(PATCH_PINECONE, return_value=[]):
            result = await execute_tool("search_ders_notlari", {"query": "xyz", "ders": "patoloji"})
        assert "patoloji" in result.lower()
        assert "bulunamad" in result.lower()

    async def test_exception_returns_error_string_not_raise(self):
        with patch(PATCH_PINECONE, side_effect=RuntimeError("timeout")):
            result = await execute_tool("search_ders_notlari", {"query": "SCC", "ders": "patoloji"})
        assert "hata" in result.lower()

    async def test_handles_plain_string_results(self):
        with patch(PATCH_PINECONE, return_value=["plain text result"]):
            result = await execute_tool("search_ders_notlari", {"query": "x", "ders": "patoloji"})
        assert "plain text result" in result


# ─── search_hafiza formatting ─────────────────────────────────────────────────

class TestSearchHafiza:

    async def test_returns_results_with_header(self):
        hits = [{"text": "You last studied patoloji yesterday."}]
        with patch(PATCH_MULTI, new=AsyncMock(return_value=hits)):
            result = await execute_tool("search_hafiza", {"query": "en son ne calistim"})
        assert "Hafiza" in result or "hafiza" in result.lower()
        assert "patoloji yesterday" in result

    async def test_empty_results_return_not_found_message(self):
        with patch(PATCH_MULTI, new=AsyncMock(return_value=[])):
            result = await execute_tool("search_hafiza", {"query": "xyz"})
        assert "bulunamad" in result.lower()

    async def test_exception_returns_error_string(self):
        with patch(PATCH_MULTI, new=AsyncMock(side_effect=RuntimeError("fail"))):
            result = await execute_tool("search_hafiza", {"query": "x"})
        assert "hata" in result.lower()


# ─── search_soru_bankasi formatting ──────────────────────────────────────────

class TestSearchSoruBankasi:

    async def test_returns_question_text_and_answer(self):
        questions = [{
            "question_text": "Hangisi dogrudur?",
            "correct_answer": "A",
            "explanation": "A dogrudur cunku...",
        }]
        with patch(PATCH_QUESTIONS, return_value=questions):
            result = await execute_tool("search_soru_bankasi", {"query": "dogru cevap"})
        assert "Hangisi dogrudur?" in result
        assert "Cevap: A" in result
        assert "A dogrudur" in result

    async def test_empty_results_return_not_found_message(self):
        with patch(PATCH_QUESTIONS, return_value=[]):
            result = await execute_tool("search_soru_bankasi", {"query": "xyz"})
        assert "bulunamad" in result.lower()

    async def test_optional_ders_parameter_passed_through(self):
        with patch(PATCH_QUESTIONS, return_value=[]) as mock_q:
            await execute_tool("search_soru_bankasi", {"query": "SCC", "ders": "patoloji"})
        call_args = mock_q.call_args
        assert "patoloji" in call_args.args or "patoloji" in str(call_args)

    async def test_exception_returns_error_string(self):
        with patch(PATCH_QUESTIONS, side_effect=RuntimeError("db error")):
            result = await execute_tool("search_soru_bankasi", {"query": "x"})
        assert "hata" in result.lower()


# ─── search_anki formatting ───────────────────────────────────────────────────

class TestSearchAnki:

    async def test_returns_card_text_with_header(self):
        hits = [{"text": "Protez kron nedir: tam porselen"}]
        with patch(PATCH_PINECONE, return_value=hits):
            result = await execute_tool("search_anki", {"query": "protez", "ders": "protez"})
        assert "PROTEZ" in result
        assert "Protez kron nedir" in result

    async def test_empty_results_return_not_found_message(self):
        with patch(PATCH_PINECONE, return_value=[]):
            result = await execute_tool("search_anki", {"query": "xyz", "ders": "protez"})
        assert "bulunamad" in result.lower()

    async def test_exception_returns_error_string(self):
        with patch(PATCH_PINECONE, side_effect=RuntimeError("timeout")):
            result = await execute_tool("search_anki", {"query": "x", "ders": "protez"})
        assert "hata" in result.lower()
