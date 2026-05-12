"""Tests for bot/main.py — cache helpers, auth guard, webhook endpoint."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Cache helper functions
# ---------------------------------------------------------------------------

class TestGetSearchCacheKey:
    def setup_method(self):
        from bot.main import get_search_cache_key
        self.fn = get_search_cache_key

    def test_basic_key_format(self):
        key = self.fn("patoloji nedir", "ders_calis", "myppdfs")
        assert "patoloji nedir" in key
        assert "ders_calis" in key
        assert "myppdfs" in key

    def test_none_forced_index_produces_empty_segment(self):
        key = self.fn("sorgu", "genel", None)
        assert key.endswith("|")

    def test_long_query_truncated_to_100(self):
        long_query = "x" * 200
        key = self.fn(long_query, "genel", None)
        # The query segment (before first |) should be ≤100 chars
        query_part = key.split("|")[0]
        assert len(query_part) == 100

    def test_same_inputs_produce_same_key(self):
        k1 = self.fn("sorgu", "ders_calis", "myppdfs")
        k2 = self.fn("sorgu", "ders_calis", "myppdfs")
        assert k1 == k2

    def test_different_intents_produce_different_keys(self):
        k1 = self.fn("sorgu", "ders_calis", None)
        k2 = self.fn("sorgu", "hafiza", None)
        assert k1 != k2


# ---------------------------------------------------------------------------
# is_allowed
# ---------------------------------------------------------------------------

class TestIsAllowed:
    def test_allowed_chat_id_returns_true(self):
        with patch("bot.main.ALLOWED_CHAT_IDS", {123456}):
            from bot.main import is_allowed
            assert is_allowed(123456) is True

    def test_disallowed_chat_id_returns_false(self):
        with patch("bot.main.ALLOWED_CHAT_IDS", {123456}):
            from bot.main import is_allowed
            assert is_allowed(999999) is False

    def test_empty_allowed_list_permits_all(self):
        with patch("bot.main.ALLOWED_CHAT_IDS", set()):
            from bot.main import is_allowed
            assert is_allowed(999999) is True
            assert is_allowed(0) is True


# ---------------------------------------------------------------------------
# Context cache helpers
# ---------------------------------------------------------------------------

class TestContextHelpers:
    def setup_method(self):
        import cachetools
        from bot import main
        # Reset the caches between tests
        main.conv_context = cachetools.TTLCache(maxsize=100, ttl=3600)
        main.user_settings = cachetools.TTLCache(maxsize=100, ttl=3600 * 24)

    def test_get_context_creates_default(self):
        from bot.main import get_context
        ctx = get_context(111)
        assert "history" in ctx
        assert ctx["ders"] is None

    def test_get_context_same_object_returned(self):
        from bot.main import get_context
        ctx1 = get_context(222)
        ctx2 = get_context(222)
        assert ctx1 is ctx2

    def test_clear_context_removes_entry(self):
        from bot.main import get_context, clear_context
        get_context(333)
        clear_context(333)
        # After clearing, getting context again creates a fresh one
        ctx = get_context(333)
        assert ctx["history"] == []

    def test_clear_nonexistent_context_does_not_raise(self):
        from bot.main import clear_context
        clear_context(99999)  # Should not raise


class TestSettingsHelpers:
    def setup_method(self):
        import cachetools
        from bot import main
        main.user_settings = cachetools.TTLCache(maxsize=100, ttl=3600 * 24)

    def test_get_settings_returns_defaults(self):
        from bot.main import get_settings
        from bot.settings import USER_SETTINGS_DEFAULTS
        settings = get_settings(444)
        assert settings == USER_SETTINGS_DEFAULTS

    def test_get_settings_same_object_on_second_call(self):
        from bot.main import get_settings
        s1 = get_settings(555)
        s2 = get_settings(555)
        assert s1 is s2

    def test_update_settings_persists(self):
        from bot.main import get_settings, update_settings
        update_settings(666, {"model": "deepseek-reasoner", "speed_mode": "fast"})
        result = get_settings(666)
        assert result["model"] == "deepseek-reasoner"
        assert result["speed_mode"] == "fast"


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

class TestWebhookEndpoint:
    @pytest.fixture(autouse=True)
    def patch_handlers_and_send(self, monkeypatch):
        self.mock_send = AsyncMock()
        self.mock_handle_message = AsyncMock()
        self.mock_cmd_start = AsyncMock()
        self.mock_cmd_help = AsyncMock()
        self.mock_cmd_sifirla = AsyncMock()

        monkeypatch.setattr("bot.main.send", self.mock_send)
        monkeypatch.setattr("bot.main.handle_message", self.mock_handle_message)
        monkeypatch.setattr("bot.main.cmd_start", self.mock_cmd_start)
        monkeypatch.setattr("bot.main.cmd_help", self.mock_cmd_help)
        monkeypatch.setattr("bot.main.cmd_sifirla", self.mock_cmd_sifirla)
        monkeypatch.setattr("bot.main.send_action", AsyncMock())

        # Ensure an allowed chat ID
        monkeypatch.setattr("bot.main.ALLOWED_CHAT_IDS", {123456})

    def _make_request(self, chat_id=123456, text="merhaba"):
        return {
            "message": {
                "chat": {"id": chat_id},
                "text": text,
            }
        }

    async def test_health_endpoint_returns_ok(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_normal_message_dispatched_to_handle_message(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        payload = self._make_request(text="patoloji nedir")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
        assert resp.status_code == 200
        self.mock_handle_message.assert_called_once()

    async def test_start_command_dispatched(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        payload = self._make_request(text="/start")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/webhook", json=payload)
        self.mock_cmd_start.assert_called_once()

    async def test_help_command_dispatched(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        payload = self._make_request(text="/help")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/webhook", json=payload)
        self.mock_cmd_help.assert_called_once()

    async def test_sifirla_command_dispatched(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        payload = self._make_request(text="/sifirla")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/webhook", json=payload)
        self.mock_cmd_sifirla.assert_called_once()

    async def test_unauthorized_chat_id_blocked(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        payload = self._make_request(chat_id=999999, text="merhaba")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
        assert resp.status_code == 200
        self.mock_handle_message.assert_not_called()
        self.mock_send.assert_called_once()
        sent_text = self.mock_send.call_args[0][1]
        assert "yetki" in sent_text.lower() or "yetkini" in sent_text.lower() or "yok" in sent_text.lower()

    async def test_empty_message_returns_200_no_dispatch(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        payload = {"message": {"chat": {"id": 123456}, "text": ""}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
        assert resp.status_code == 200
        self.mock_handle_message.assert_not_called()

    async def test_no_message_field_returns_200(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json={"update_id": 1})
        assert resp.status_code == 200

    async def test_webhook_exception_does_not_crash(self):
        from httpx import AsyncClient, ASGITransport
        from bot.main import app
        self.mock_handle_message.side_effect = Exception("unexpected crash")
        payload = self._make_request(text="patoloji nedir")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# send() chunking logic
# ---------------------------------------------------------------------------

class TestSendChunking:
    async def test_short_message_sent_as_single_chunk(self):
        with patch("bot.main.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            from bot.main import send
            await send(123, "Kısa mesaj")
            assert mock_client.post.call_count == 1

    async def test_long_message_split_into_chunks(self):
        with patch("bot.main.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            from bot.main import send
            long_text = "x" * 8500  # > 4000 chars → 3 chunks
            await send(123, long_text)
            assert mock_client.post.call_count == 3

    async def test_reply_markup_only_on_first_chunk(self):
        with patch("bot.main.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            from bot.main import send
            long_text = "x" * 8500
            await send(123, long_text, reply_markup='{"inline_keyboard": []}')

            calls = mock_client.post.call_args_list
            first_payload = calls[0][1]["json"]
            assert "reply_markup" in first_payload
            for subsequent_call in calls[1:]:
                payload = subsequent_call[1]["json"]
                assert "reply_markup" not in payload
