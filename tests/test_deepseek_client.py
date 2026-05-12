"""Tests for bot/services/deepseek_client.py — API wrapper with retry."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call


def _make_response(content="Test yanıtı", tool_calls=None, finish_reason="stop"):
    msg = MagicMock()
    msg.content = content
    mock_tool_calls = []
    for tc in (tool_calls or []):
        m = MagicMock()
        m.id = tc["id"]
        m.function.name = tc["name"]
        m.function.arguments = tc["arguments"]
        mock_tool_calls.append(m)
    msg.tool_calls = mock_tool_calls or None

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 20
    usage.total_tokens = 30

    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message = msg
    resp.choices[0].finish_reason = finish_reason
    resp.usage = usage
    return resp


class TestDeepseekChat:
    @pytest.fixture(autouse=True)
    def patch_deepseek(self, monkeypatch):
        self.mock_deepseek = AsyncMock()
        monkeypatch.setattr("bot.services.deepseek_client.deepseek", self.mock_deepseek)

    async def test_successful_text_response(self):
        from bot.services.deepseek_client import chat
        self.mock_deepseek.chat.completions.create = AsyncMock(
            return_value=_make_response("Yanıt metni")
        )
        result = await chat([{"role": "user", "content": "merhaba"}])
        assert result["content"] == "Yanıt metni"
        assert result["tool_calls"] == []
        assert result["finish_reason"] == "stop"

    async def test_tool_calls_parsed_correctly(self):
        from bot.services.deepseek_client import chat
        tool_calls = [{"id": "call_1", "name": "search_ders_notlari", "arguments": '{"query": "test"}'}]
        self.mock_deepseek.chat.completions.create = AsyncMock(
            return_value=_make_response(tool_calls=tool_calls)
        )
        result = await chat([{"role": "user", "content": "soru"}], tools=[{"type": "function"}])
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "search_ders_notlari"
        assert result["tool_calls"][0]["id"] == "call_1"

    async def test_tools_added_to_kwargs_when_provided(self):
        from bot.services.deepseek_client import chat
        self.mock_deepseek.chat.completions.create = AsyncMock(
            return_value=_make_response()
        )
        tool_defs = [{"type": "function", "function": {"name": "test_tool"}}]
        await chat([{"role": "user", "content": "soru"}], tools=tool_defs)
        call_kwargs = self.mock_deepseek.chat.completions.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tool_choice"] == "auto"

    async def test_no_tools_no_tool_kwargs(self):
        from bot.services.deepseek_client import chat
        self.mock_deepseek.chat.completions.create = AsyncMock(return_value=_make_response())
        await chat([{"role": "user", "content": "soru"}])
        call_kwargs = self.mock_deepseek.chat.completions.create.call_args[1]
        assert "tools" not in call_kwargs

    async def test_retry_on_failure_then_succeed(self):
        from bot.services.deepseek_client import chat
        self.mock_deepseek.chat.completions.create = AsyncMock(
            side_effect=[Exception("Geçici hata"), _make_response("Yeniden deneme yanıtı")]
        )
        with patch("bot.services.deepseek_client.asyncio.sleep", new_callable=AsyncMock):
            result = await chat([{"role": "user", "content": "soru"}])
        assert result["content"] == "Yeniden deneme yanıtı"
        assert self.mock_deepseek.chat.completions.create.call_count == 2

    async def test_all_retries_fail_raises(self):
        from bot.services.deepseek_client import chat, MAX_RETRIES
        self.mock_deepseek.chat.completions.create = AsyncMock(
            side_effect=Exception("Kalıcı hata")
        )
        with patch("bot.services.deepseek_client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Kalıcı hata"):
                await chat([{"role": "user", "content": "soru"}])
        assert self.mock_deepseek.chat.completions.create.call_count == MAX_RETRIES + 1

    async def test_model_override(self):
        from bot.services.deepseek_client import chat
        self.mock_deepseek.chat.completions.create = AsyncMock(return_value=_make_response())
        await chat([{"role": "user", "content": "soru"}], model="deepseek-reasoner")
        call_kwargs = self.mock_deepseek.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "deepseek-reasoner"

    async def test_default_model_used_when_not_overridden(self):
        from bot.services.deepseek_client import chat
        from bot.settings import DEEPSEEK_MODEL
        self.mock_deepseek.chat.completions.create = AsyncMock(return_value=_make_response())
        await chat([{"role": "user", "content": "soru"}])
        call_kwargs = self.mock_deepseek.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == DEEPSEEK_MODEL
