"""Tests for bot/services/agent_loop.py — DeepSeek agent loop."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# _format_context
# ---------------------------------------------------------------------------

class TestFormatContext:
    def setup_method(self):
        from bot.services.agent_loop import _format_context
        self.fn = _format_context

    def test_empty_results_returns_empty_string(self):
        assert self.fn({}) == ""

    def test_pdfs_section_included(self):
        results = {"pdfs": [{"text": "patoloji notu"}]}
        output = self.fn(results)
        assert "DERS NOTLARI" in output
        assert "patoloji notu" in output

    def test_brain_section_included(self):
        results = {"brain": [{"text": "hafıza kaydı"}]}
        output = self.fn(results)
        assert "HAFIZA" in output
        assert "hafıza kaydı" in output

    def test_questions_section_included(self):
        results = {"questions": [{"question_text": "soru metni"}]}
        output = self.fn(results)
        assert "DUS SORULARI" in output
        assert "soru metni" in output

    def test_anki_section_included(self):
        results = {"anki": [{"text": "anki kartı"}]}
        output = self.fn(results)
        assert "ANKI KARTLARI" in output
        assert "anki kartı" in output

    def test_all_sections_combined(self):
        results = {
            "pdfs": [{"text": "ders notu"}],
            "brain": [{"text": "hafıza"}],
            "questions": [{"question_text": "soru"}],
            "anki": [{"text": "kart"}],
        }
        output = self.fn(results)
        assert "DERS NOTLARI" in output
        assert "HAFIZA" in output
        assert "DUS SORULARI" in output
        assert "ANKI KARTLARI" in output

    def test_non_dict_results_handled(self):
        results = {"pdfs": ["düz string sonuç"]}
        output = self.fn(results)
        assert "düz string sonuç" in output

    def test_capped_at_five_pdfs(self):
        results = {"pdfs": [{"text": f"sonuç {i}"} for i in range(10)]}
        output = self.fn(results)
        # Only first 5 should appear
        assert "sonuç 4" in output
        assert "sonuç 5" not in output

    def test_questions_use_question_fallback_key(self):
        results = {"questions": [{"question": "alternatif soru anahtarı"}]}
        output = self.fn(results)
        assert "alternatif soru anahtarı" in output


# ---------------------------------------------------------------------------
# run_agent
# ---------------------------------------------------------------------------

class TestRunAgent:
    @pytest.fixture(autouse=True)
    def patch_chat(self, monkeypatch):
        self.mock_chat = AsyncMock()
        monkeypatch.setattr("bot.services.agent_loop.chat", self.mock_chat)
        self.mock_execute_tool = AsyncMock(return_value="tool result")
        monkeypatch.setattr("bot.services.agent_loop.execute_tool", self.mock_execute_tool)

    def _make_text_response(self, content="Yanıt metni"):
        return {"content": content, "tool_calls": [], "finish_reason": "stop"}

    def _make_tool_response(self, tool_name="search_ders_notlari", args='{"query": "test", "ders": "patoloji"}'):
        return {
            "content": None,
            "tool_calls": [{"id": "call_1", "name": tool_name, "arguments": args}],
            "finish_reason": "tool_calls",
        }

    async def test_fast_mode_single_iteration(self):
        from bot.services.agent_loop import run_agent
        self.mock_chat.return_value = self._make_text_response("Hızlı yanıt")
        result = await run_agent("soru", {}, settings={"speed_mode": "fast"})
        assert result == "Hızlı yanıt"
        assert self.mock_chat.call_count == 1

    async def test_text_response_returned_immediately(self):
        from bot.services.agent_loop import run_agent
        self.mock_chat.return_value = self._make_text_response("Doğrudan yanıt")
        result = await run_agent("patoloji nedir", {"pdfs": [{"text": "not"}]})
        assert result == "Doğrudan yanıt"

    async def test_tool_call_executes_tool_and_continues(self):
        from bot.services.agent_loop import run_agent
        self.mock_chat.side_effect = [
            self._make_tool_response(),
            self._make_text_response("Araç çağrısı sonrası yanıt"),
        ]
        result = await run_agent("patoloji nedir", {})
        assert result == "Araç çağrısı sonrası yanıt"
        self.mock_execute_tool.assert_called_once()

    async def test_max_iterations_returns_limit_message(self):
        from bot.services.agent_loop import run_agent
        # Always returns tool calls → exhausts iterations
        self.mock_chat.return_value = self._make_tool_response()
        result = await run_agent("soru", {}, settings={"agent_iterations": 2})
        assert "limit" in result.lower() or "arama limitine" in result

    async def test_tool_error_handled_gracefully(self):
        from bot.services.agent_loop import run_agent
        self.mock_execute_tool.side_effect = Exception("tool crash")
        self.mock_chat.side_effect = [
            self._make_tool_response(),
            self._make_text_response("Hata sonrası yanıt"),
        ]
        result = await run_agent("soru", {})
        assert result == "Hata sonrası yanıt"

    async def test_empty_content_falls_back_to_default(self):
        from bot.services.agent_loop import run_agent
        self.mock_chat.return_value = {"content": "", "tool_calls": [], "finish_reason": "stop"}
        result = await run_agent("soru", {})
        assert result  # Should not be empty

    async def test_context_injected_in_first_message(self):
        from bot.services.agent_loop import run_agent
        self.mock_chat.return_value = self._make_text_response()
        await run_agent("kullanıcı sorusu", {"pdfs": [{"text": "ders notu içeriği"}]})
        call_args = self.mock_chat.call_args
        messages = call_args[0][0]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert "kullanıcı sorusu" in user_msg["content"]
        assert "ders notu içeriği" in user_msg["content"]

    async def test_fast_mode_uses_fast_prompt(self):
        from bot.services.agent_loop import run_agent
        from bot.prompts.system_prompt import SYSTEM_PROMPT_FAST
        self.mock_chat.return_value = self._make_text_response()
        await run_agent("soru", {}, settings={"speed_mode": "fast"})
        messages = self.mock_chat.call_args[0][0]
        system_msg = next(m for m in messages if m["role"] == "system")
        assert system_msg["content"] == SYSTEM_PROMPT_FAST

    async def test_tool_result_truncated_to_8000_chars(self):
        from bot.services.agent_loop import run_agent
        long_result = "x" * 10000
        self.mock_execute_tool.return_value = long_result
        self.mock_chat.side_effect = [
            self._make_tool_response(),
            self._make_text_response(),
        ]
        await run_agent("soru", {})
        messages = self.mock_chat.call_args[0][0]
        tool_msg = next(m for m in messages if m["role"] == "tool")
        assert len(tool_msg["content"]) <= 8000
