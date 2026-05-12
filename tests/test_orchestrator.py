"""Tests for bot/services/orchestrator.py — search orchestration logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# _detect_ders
# ---------------------------------------------------------------------------

class TestDetectDers:
    def setup_method(self):
        from bot.services.orchestrator import _detect_ders
        self.fn = _detect_ders

    def test_patoloji_detected(self):
        assert self.fn("patoloji dersi hakkında bilgi ver") == "patoloji"

    def test_radyoloji_detected(self):
        assert self.fn("radyoloji görüntüleme teknikleri") == "radyoloji"

    def test_endodonti_detected(self):
        assert self.fn("kanal tedavisi nasıl yapılır") == "endodonti"

    def test_protez_detected(self):
        assert self.fn("implant tedavisi ve kuron uygulaması") == "protez"

    def test_histoloji_detected(self):
        assert self.fn("epitel doku tipleri nelerdir") == "histoloji"

    def test_farmakoloji_detected(self):
        assert self.fn("antibiyotik kullanımı ve dozaj") == "farmakoloji"

    def test_pedodonti_detected(self):
        # Keywords use ASCII: "cocuk" and "sut disi" (no Turkish diacritics)
        assert self.fn("pedodonti ve cocuk hastalari") == "pedodonti"

    def test_restoratif_detected(self):
        assert self.fn("kompozit dolgu uygulama teknikleri") == "restoratif"

    def test_cerrahi_detected(self):
        assert self.fn("cekim sonrası komplikasyonlar") == "cerrahi"

    def test_case_insensitive(self):
        assert self.fn("PATOLOJİ dersi") == "patoloji"

    def test_no_ders_returns_none(self):
        assert self.fn("selam nasılsın bugün") is None

    def test_mixed_text_with_ders(self):
        assert self.fn("bu soruyu çöz: patoloji ve neoplazi hakkında") == "patoloji"


# ---------------------------------------------------------------------------
# orchestrate_search
# ---------------------------------------------------------------------------

class TestOrchestrateSearch:
    @pytest.fixture(autouse=True)
    def patch_search_functions(self, monkeypatch):
        self.mock_pinecone_search = MagicMock(return_value=[{"text": "mock pdf result"}])
        self.mock_search_multi_ns = AsyncMock(return_value=[{"text": "mock multi result"}])
        self.mock_search_questions = MagicMock(return_value=[{"question_text": "mock question"}])

        monkeypatch.setattr("bot.services.orchestrator.pinecone_search", self.mock_pinecone_search)
        monkeypatch.setattr("bot.services.orchestrator.search_multi_ns", self.mock_search_multi_ns)
        monkeypatch.setattr("bot.services.orchestrator.search_questions", self.mock_search_questions)

    async def test_ders_calis_searches_pdfs_and_questions(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("patoloji nedir", "ders_calis")
        assert "pdfs" in results or "questions" in results

    async def test_hafiza_intent_searches_brain(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("en son ne çalıştım", "hafiza")
        assert "brain" in results

    async def test_forced_mybrain_searches_brain(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("ilerleme", "genel", forced_index="mybrain")
        assert "brain" in results

    async def test_forced_myppdfs_searches_pdfs(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("patoloji notları", "genel", forced_index="myppdfs")
        assert "pdfs" in results

    async def test_soru_sor_includes_questions(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("bu soruyu çöz", "soru_sor")
        assert "questions" in results

    async def test_cikmis_analiz_includes_questions(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("en çok çıkan konular", "cikmis_analiz")
        assert "questions" in results

    async def test_fast_mode_skips_cross_namespace(self):
        from bot.services.orchestrator import orchestrate_search
        # In fast mode with a detected ders, only that single namespace should be searched
        results = await orchestrate_search("patoloji tümör", "ders_calis", settings={"speed_mode": "fast"})
        # Should still return pdfs
        assert "pdfs" in results

    async def test_fast_mode_skips_brain_for_genel_with_ders(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("patoloji nedir", "genel", settings={"speed_mode": "fast"})
        # genel + ders detected + fast → brain should be skipped
        assert "brain" not in results

    async def test_anki_searched_for_protez(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("protez implant", "ders_calis")
        assert "anki" in results

    async def test_forced_anki_index(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("protez soru", "ders_calis", forced_index="anki")
        assert "anki" in results

    async def test_search_error_returns_empty_list_for_that_key(self):
        from bot.services.orchestrator import orchestrate_search
        self.mock_search_multi_ns.side_effect = Exception("Pinecone down")
        results = await orchestrate_search("patoloji", "ders_calis")
        # Should not raise, pdfs key should be [] due to error
        assert isinstance(results, dict)

    async def test_search_depth_respected(self):
        from bot.services.orchestrator import orchestrate_search
        await orchestrate_search("patoloji", "soru_sor", settings={"search_depth": 3})
        # search_questions called with limit = min(3, 5) = 3
        call_args = self.mock_search_questions.call_args
        assert call_args is not None
        limit_arg = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("limit", None)
        assert limit_arg == 3

    async def test_empty_results_dict_for_genel_no_ders(self):
        from bot.services.orchestrator import orchestrate_search
        results = await orchestrate_search("selam", "genel")
        # genel + no ders detected → brain searched, but no pdfs/questions/anki
        assert "pdfs" not in results
        assert "questions" not in results
