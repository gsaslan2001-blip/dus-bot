"""Tests for bot/services/router.py — intent classification pipeline."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# _prefix_intent
# ---------------------------------------------------------------------------

class TestPrefixIntent:
    def setup_method(self):
        from bot.services.router import _prefix_intent
        self.fn = _prefix_intent

    def test_pdf_prefix_returns_ders_calis(self):
        intent, forced_index, cleaned = self.fn("/mypdf SCC patogenezi")
        assert intent == "ders_calis"
        assert forced_index == "myppdfs"
        assert cleaned == "SCC patogenezi"

    def test_brain_prefix_returns_hafiza(self):
        intent, forced_index, cleaned = self.fn("/brain en son ne çalıştım")
        assert intent == "hafiza"
        assert forced_index == "mybrain"
        assert cleaned == "en son ne çalıştım"

    def test_soru_prefix_returns_soru_sor(self):
        intent, forced_index, _ = self.fn("/soru kanal tedavisi nedir")
        assert intent == "soru_sor"
        assert forced_index is None

    def test_anki_prefix_returns_ders_calis_with_anki_index(self):
        intent, forced_index, _ = self.fn("/anki protez soruları")
        assert intent == "ders_calis"
        assert forced_index == "anki"

    def test_cikmis_prefix_returns_cikmis_analiz(self):
        intent, forced_index, _ = self.fn("/cikmis en çok çıkan konular")
        assert intent == "cikmis_analiz"

    def test_case_insensitive_prefix(self):
        result = self.fn("/PDF patoloji notları")
        assert result is not None
        assert result[0] == "ders_calis"

    def test_prefix_with_no_remainder_keeps_original(self):
        intent, _, cleaned = self.fn("/mypdf")
        assert intent == "ders_calis"
        assert cleaned == "/mypdf"

    def test_no_prefix_returns_none(self):
        assert self.fn("patoloji nedir?") is None

    def test_prefix_aliases_work(self):
        for prefix in ["/pdfs", "/pdf", "/ders", "/not"]:
            result = self.fn(f"{prefix} test mesajı")
            assert result is not None, f"Prefix {prefix} should match"
            assert result[0] == "ders_calis"

    def test_memory_aliases_work(self):
        for prefix in ["/hafiza", "/memory", "/ilerleme"]:
            result = self.fn(f"{prefix} test")
            assert result is not None
            assert result[0] == "hafiza"


# ---------------------------------------------------------------------------
# _keyword_intent
# ---------------------------------------------------------------------------

class TestKeywordIntent:
    def setup_method(self):
        from bot.services.router import _keyword_intent
        self.fn = _keyword_intent

    def test_greeting_returns_genel(self):
        assert self.fn("selam") == "genel"
        assert self.fn("merhaba") == "genel"

    def test_very_short_non_greeting_returns_none(self):
        assert self.fn("abc") is None

    def test_hafiza_keyword_detected(self):
        assert self.fn("en son ne çalışmıştım geçen hafta") == "hafiza"

    def test_soru_keyword_detected(self):
        assert self.fn("bu soruyu çözer misin lütfen") == "soru_sor"

    def test_ders_keyword_detected(self):
        assert self.fn("SCC patogenezini anlat bana") == "ders_calis"

    def test_ders_keyword_nedir(self):
        assert self.fn("patolojide karsinom nedir açıkla") == "ders_calis"

    def test_unknown_long_message_returns_none(self):
        result = self.fn("bu mesaj belirsiz bir şey içeriyor tamamen")
        assert result is None

    def test_hafiza_takes_priority_over_soru(self):
        # "kaldım" is hafiza keyword; "soru" is soru keyword — hafiza checked first
        result = self.fn("hangi soruda kaldım bilmiyorum")
        assert result == "hafiza"


# ---------------------------------------------------------------------------
# _parse_intent
# ---------------------------------------------------------------------------

class TestParseIntent:
    def setup_method(self):
        from bot.services.router import _parse_intent
        self.fn = _parse_intent

    def test_clean_json(self):
        assert self.fn('{"intent": "ders_calis"}') == "ders_calis"

    def test_all_valid_intents(self):
        for intent in ("ders_calis", "soru_sor", "cikmis_analiz", "hafiza", "genel"):
            assert self.fn(f'{{"intent": "{intent}"}}') == intent

    def test_markdown_fenced_json(self):
        text = "```json\n{\"intent\": \"soru_sor\"}\n```"
        assert self.fn(text) == "soru_sor"

    def test_markdown_fenced_no_lang(self):
        text = "```\n{\"intent\": \"hafiza\"}\n```"
        assert self.fn(text) == "hafiza"

    def test_json_embedded_in_text(self):
        text = 'Sure, here is the answer: {"intent": "cikmis_analiz"} done.'
        assert self.fn(text) == "cikmis_analiz"

    def test_invalid_json_falls_back_to_genel(self):
        assert self.fn("not valid json at all") == "genel"

    def test_unknown_intent_value_returned_as_is(self):
        # Dict parsing returns whatever value is in "intent" without validation
        assert self.fn('{"intent": "unknown_category"}') == "unknown_category"

    def test_empty_string_returns_genel(self):
        assert self.fn("") == "genel"

    def test_bare_valid_intent_string(self):
        # A bare valid intent string as JSON should be recognised
        assert self.fn('"ders_calis"') == "ders_calis"

    def test_bare_invalid_intent_string_returns_genel(self):
        assert self.fn('"random_intent"') == "genel"


# ---------------------------------------------------------------------------
# classify_intent  (async, mocks DeepSeek)
# ---------------------------------------------------------------------------

class TestClassifyIntent:
    @pytest.fixture(autouse=True)
    def patch_deepseek(self, monkeypatch):
        self.mock_deepseek = AsyncMock()
        monkeypatch.setattr("bot.services.router.deepseek", self.mock_deepseek)

    async def test_prefix_path_skips_api(self):
        from bot.services.router import classify_intent
        intent = await classify_intent("/mypdf patoloji")
        assert intent == "ders_calis"
        self.mock_deepseek.chat.completions.create.assert_not_called()

    async def test_keyword_path_skips_api(self):
        from bot.services.router import classify_intent
        intent = await classify_intent("SCC patogenezini detaylı anlat")
        assert intent == "ders_calis"
        self.mock_deepseek.chat.completions.create.assert_not_called()

    async def test_deepseek_fallback_called_for_ambiguous(self):
        from bot.services.router import classify_intent
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '{"intent": "genel"}'
        self.mock_deepseek.chat.completions.create = AsyncMock(return_value=mock_resp)
        intent = await classify_intent("tamam anladım teşekkürler")
        assert intent == "genel"
        self.mock_deepseek.chat.completions.create.assert_called_once()

    async def test_deepseek_error_falls_back_to_genel(self):
        from bot.services.router import classify_intent
        self.mock_deepseek.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        intent = await classify_intent("tamam anladım teşekkürler")
        assert intent == "genel"


# ---------------------------------------------------------------------------
# get_prefix_routing
# ---------------------------------------------------------------------------

class TestGetPrefixRouting:
    def setup_method(self):
        from bot.services.router import get_prefix_routing
        self.fn = get_prefix_routing

    def test_prefix_message_extracts_index_and_cleaned(self):
        forced_index, cleaned = self.fn("/mypdf patoloji sorusu")
        assert forced_index == "myppdfs"
        assert cleaned == "patoloji sorusu"

    def test_no_prefix_returns_none_index_and_original(self):
        forced_index, cleaned = self.fn("normal mesaj")
        assert forced_index is None
        assert cleaned == "normal mesaj"

    def test_brain_prefix_extracts_mybrain(self):
        forced_index, cleaned = self.fn("/brain ilerleme durumum")
        assert forced_index == "mybrain"
        assert cleaned == "ilerleme durumum"
