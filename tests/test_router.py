"""
Tests for bot/services/router.py

Pure functions (_prefix_intent, _keyword_intent, _parse_intent) are tested
directly without any mocking.  The async classify_intent() path is covered
by patching bot.services.router.deepseek at the module level.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.router import (
    _prefix_intent,
    _keyword_intent,
    _parse_intent,
    get_prefix_routing,
    classify_intent,
    route_message,
    get_prefix_help,
)


# ─── _prefix_intent ───────────────────────────────────────────────────────────
# _prefix_intent artık 4-tuple döndürüyor: (intent, forced_index, cleaned, is_prefix_only)

class TestPrefixIntent:

    def test_mypdf_returns_ders_calis_with_myppdfs_index(self):
        intent, forced, cleaned, is_only = _prefix_intent("/mypdf SCC patogenezi")
        assert intent == "ders_calis"
        assert forced == "myppdfs"
        assert cleaned == "SCC patogenezi"
        assert is_only is False

    def test_pdfs_alias(self):
        intent, forced, _, is_only = _prefix_intent("/pdfs Radyoloji")
        assert intent == "ders_calis"
        assert forced == "myppdfs"
        assert is_only is False

    def test_pdf_alias(self):
        intent, forced, _, __ = _prefix_intent("/pdf histoloji")
        assert intent == "ders_calis"
        assert forced == "myppdfs"

    def test_ders_alias(self):
        intent, _, __, ___ = _prefix_intent("/ders endodonti")
        assert intent == "ders_calis"

    def test_not_alias(self):
        intent, _, __, ___ = _prefix_intent("/not patoloji")
        assert intent == "ders_calis"

    def test_brain_returns_hafiza_with_mybrain_index(self):
        intent, forced, _, __ = _prefix_intent("/brain en son ne calistim")
        assert intent == "hafiza"
        assert forced == "mybrain"

    def test_hafiza_alias(self):
        intent, forced, _, __ = _prefix_intent("/hafiza ilerleme")
        assert intent == "hafiza"
        assert forced == "mybrain"

    def test_soru_returns_soru_sor_with_dusbankasi_index(self):
        """Kritik: /soru artık dusbankasi'na exclusive yönlendiriyor."""
        intent, forced, cleaned, is_only = _prefix_intent("/soru patoloji")
        assert intent == "soru_sor"
        assert forced == "dusbankasi"
        assert cleaned == "patoloji"
        assert is_only is False

    def test_quiz_alias(self):
        intent, forced, _, __ = _prefix_intent("/quiz patoloji")
        assert intent == "soru_sor"
        assert forced == "dusbankasi"

    def test_test_alias(self):
        intent, forced, _, __ = _prefix_intent("/test radyoloji")
        assert intent == "soru_sor"
        assert forced == "dusbankasi"

    def test_anki_returns_ders_calis_with_anki_index(self):
        intent, forced, _, __ = _prefix_intent("/anki protez kartlari")
        assert intent == "ders_calis"
        assert forced == "anki"

    def test_cikmis_returns_cikmis_analiz(self):
        intent, forced, _, __ = _prefix_intent("/cikmis patoloji")
        assert intent == "cikmis_analiz"
        assert forced is None

    def test_sinav_alias(self):
        intent, forced, cleaned, is_only = _prefix_intent("/sinav")
        assert intent == "cikmis_analiz"
        assert is_only is True
        assert cleaned == ""

    def test_no_prefix_returns_none(self):
        assert _prefix_intent("SCC patogenezini anlat") is None

    def test_case_insensitive(self):
        intent, _, __, ___ = _prefix_intent("/MYPDF SCC")
        assert intent == "ders_calis"

    def test_whitespace_trimmed_before_matching(self):
        intent, _, cleaned, is_only = _prefix_intent("  /mypdf   SCC  ")
        assert intent == "ders_calis"
        assert cleaned == "SCC"
        assert is_only is False

    def test_prefix_only_returns_empty_cleaned_and_is_only_true(self):
        """Kritik bug fix: /brain tek başına yazılınca empty cleaned, is_prefix_only=True döner."""
        intent, forced, cleaned, is_only = _prefix_intent("/brain")
        assert intent == "hafiza"
        assert forced == "mybrain"
        assert cleaned == ""
        assert is_only is True

    def test_mypdf_prefix_only(self):
        _, _, cleaned, is_only = _prefix_intent("/mypdf")
        assert cleaned == ""
        assert is_only is True

    def test_soru_prefix_only(self):
        _, forced, cleaned, is_only = _prefix_intent("/soru")
        assert forced == "dusbankasi"
        assert cleaned == ""
        assert is_only is True

    def test_anki_prefix_only(self):
        _, _, cleaned, is_only = _prefix_intent("/anki")
        assert cleaned == ""
        assert is_only is True

    def test_cleaned_message_strips_prefix(self):
        _, _, cleaned, _ = _prefix_intent("/soru Hangisi dogrudur?")
        assert cleaned == "Hangisi dogrudur?"


# ─── _keyword_intent ──────────────────────────────────────────────────────────

class TestKeywordIntent:

    def test_greeting_selam_returns_genel(self):
        assert _keyword_intent("selam") == "genel"

    def test_greeting_merhaba_returns_genel(self):
        assert _keyword_intent("merhaba") == "genel"

    def test_short_non_greeting_returns_none(self):
        assert _keyword_intent("ne var?") is None

    def test_hafiza_keyword_en_son(self):
        assert _keyword_intent("en son ne calistim") == "hafiza"

    def test_hafiza_keyword_ilerleme(self):
        assert _keyword_intent("ilerleme durumum nerede") == "hafiza"

    def test_hafiza_keyword_nerede_kaldim(self):
        assert _keyword_intent("nerede kaldim bilmiyorum") == "hafiza"

    def test_soru_keyword_hangisi(self):
        assert _keyword_intent("asagidakilerden hangisi dogrudur") == "soru_sor"

    def test_soru_keyword_cevap(self):
        assert _keyword_intent("bu sorunun cevabi nedir acaba") == "soru_sor"

    def test_ders_keyword_anlat(self):
        assert _keyword_intent("SCC patogenezini anlat bana") == "ders_calis"

    def test_ders_keyword_nedir(self):
        assert _keyword_intent("periodontitis nedir acikla") == "ders_calis"

    def test_ders_keyword_patogenez(self):
        assert _keyword_intent("SCC patogenezi hakkinda bilgi ver") == "ders_calis"

    def test_uncertain_long_message_returns_none(self):
        assert _keyword_intent("tamam anladim tesekkur ederim iyi gunler") is None

    def test_hafiza_checked_before_soru(self):
        result = _keyword_intent("en son cozduğum soru neydi")
        assert result == "hafiza"


# ─── _parse_intent ────────────────────────────────────────────────────────────

class TestParseIntent:

    @pytest.mark.parametrize("intent_val", [
        "ders_calis", "soru_sor", "cikmis_analiz", "hafiza", "genel"
    ])
    def test_valid_json_intents(self, intent_val: str):
        assert _parse_intent(f'{{"intent": "{intent_val}"}}') == intent_val

    def test_json_inside_markdown_fence_with_language(self):
        text = '```json\n{"intent": "ders_calis"}\n```'
        assert _parse_intent(text) == "ders_calis"

    def test_json_inside_markdown_fence_without_language(self):
        text = '```\n{"intent": "soru_sor"}\n```'
        assert _parse_intent(text) == "soru_sor"

    def test_json_embedded_in_prose(self):
        text = 'The classification result is {"intent": "hafiza"} as requested.'
        assert _parse_intent(text) == "hafiza"

    def test_invalid_json_falls_back_to_genel(self):
        assert _parse_intent("definitely not json") == "genel"

    def test_empty_string_falls_back_to_genel(self):
        assert _parse_intent("") == "genel"

    def test_unknown_intent_value_falls_back_to_genel(self):
        assert _parse_intent('{"intent": "unknown_category"}') == "genel"

    def test_leading_and_trailing_whitespace_stripped(self):
        assert _parse_intent('  {"intent": "hafiza"}  ') == "hafiza"

    def test_bare_valid_string_returns_correct_intent(self):
        assert _parse_intent('"ders_calis"') == "ders_calis"

    def test_bare_invalid_string_falls_back_to_genel(self):
        assert _parse_intent('"unknown_value"') == "genel"


# ─── get_prefix_routing ───────────────────────────────────────────────────────

class TestGetPrefixRouting:

    def test_returns_forced_index_and_cleaned_message(self):
        forced, cleaned = get_prefix_routing("/mypdf SCC patoloji")
        assert forced == "myppdfs"
        assert cleaned == "SCC patoloji"

    def test_no_prefix_returns_none_and_original_message(self):
        forced, cleaned = get_prefix_routing("SCC patoloji anlat")
        assert forced is None
        assert cleaned == "SCC patoloji anlat"

    def test_anki_prefix_returns_anki_index(self):
        forced, _ = get_prefix_routing("/anki protez")
        assert forced == "anki"

    def test_brain_prefix_returns_mybrain_index(self):
        forced, _ = get_prefix_routing("/brain notlarim")
        assert forced == "mybrain"

    def test_soru_prefix_returns_dusbankasi(self):
        forced, cleaned = get_prefix_routing("/soru patoloji sorusu")
        assert forced == "dusbankasi"
        assert cleaned == "patoloji sorusu"

    def test_prefix_only_returns_empty_cleaned(self):
        """Prefix-only artık orijinal metni değil empty string döndürüyor."""
        forced, cleaned = get_prefix_routing("/brain")
        assert forced == "mybrain"
        assert cleaned == ""


# ─── route_message ────────────────────────────────────────────────────────────

class TestRouteMessage:

    def test_prefix_with_query_returns_intent_and_index(self):
        intent, forced, cleaned, is_only = route_message("/mypdf SCC patogenezi")
        assert intent == "ders_calis"
        assert forced == "myppdfs"
        assert cleaned == "SCC patogenezi"
        assert is_only is False

    def test_prefix_only_sets_is_prefix_only(self):
        intent, forced, cleaned, is_only = route_message("/brain")
        assert intent == "hafiza"
        assert forced == "mybrain"
        assert cleaned == ""
        assert is_only is True

    def test_no_prefix_returns_none_intent_override(self):
        intent, forced, cleaned, is_only = route_message("SCC patogenezi anlat")
        assert intent is None
        assert forced is None
        assert cleaned == "SCC patogenezi anlat"
        assert is_only is False

    def test_soru_routes_to_dusbankasi(self):
        intent, forced, cleaned, is_only = route_message("/soru patoloji sorusu")
        assert intent == "soru_sor"
        assert forced == "dusbankasi"
        assert is_only is False

    def test_anki_prefix_only(self):
        _, forced, cleaned, is_only = route_message("/anki")
        assert forced == "anki"
        assert cleaned == ""
        assert is_only is True


# ─── get_prefix_help ──────────────────────────────────────────────────────────

class TestGetPrefixHelp:

    def test_myppdfs_help_not_empty(self):
        msg = get_prefix_help("myppdfs")
        assert len(msg) > 10
        assert "ders" in msg.lower() or "not" in msg.lower()

    def test_mybrain_help_not_empty(self):
        msg = get_prefix_help("mybrain")
        assert len(msg) > 10

    def test_dusbankasi_help_not_empty(self):
        msg = get_prefix_help("dusbankasi")
        assert "soru" in msg.lower()

    def test_anki_help_not_empty(self):
        msg = get_prefix_help("anki")
        assert "anki" in msg.lower()

    def test_none_forced_index_has_help(self):
        msg = get_prefix_help(None)
        assert len(msg) > 5

    def test_unknown_index_has_fallback(self):
        msg = get_prefix_help("unknown_index")
        assert len(msg) > 5


# ─── classify_intent ──────────────────────────────────────────────────────────

class TestClassifyIntent:

    async def test_prefix_fast_path_returns_correct_intent(self):
        result = await classify_intent("/mypdf SCC patogenezi")
        assert result == "ders_calis"

    async def test_keyword_fast_path_returns_correct_intent(self):
        result = await classify_intent("SCC patogenezini detayli anlat")
        assert result == "ders_calis"

    async def test_keyword_path_skips_llm(self):
        import bot.services.router as router_mod
        original = router_mod.deepseek
        spy = MagicMock()
        router_mod.deepseek = spy
        try:
            await classify_intent("SCC patogenezini detayli anlat")
            spy.chat.completions.create.assert_not_called()
        finally:
            router_mod.deepseek = original

    async def test_llm_fallback_parses_response(self):
        import bot.services.router as router_mod
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"intent": "cikmis_analiz"}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        original = router_mod.deepseek
        router_mod.deepseek = mock_client
        try:
            result = await classify_intent("ne yapmam gerekiyor ki simdi")
            assert result == "cikmis_analiz"
        finally:
            router_mod.deepseek = original

    async def test_llm_exception_returns_genel(self):
        import bot.services.router as router_mod
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        original = router_mod.deepseek
        router_mod.deepseek = mock_client
        try:
            result = await classify_intent("ne yapmam gerekiyor ki simdi")
            assert result == "genel"
        finally:
            router_mod.deepseek = original
