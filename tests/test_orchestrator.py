"""
Tests for bot/services/orchestrator.py

_detect_ders() is a pure function tested directly.
orchestrate_search() is tested by patching the three search functions that
are bound in the orchestrator module's namespace at import time.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.orchestrator import _detect_ders, orchestrate_search


# ─── _detect_ders ─────────────────────────────────────────────────────────────

class TestDetectDers:

    @pytest.mark.parametrize("query,expected", [
        ("patoloji hakkinda bilgi ver", "patoloji"),
        ("tumor ve neoplazi nedir", "patoloji"),
        ("radyoloji goruntuleme yontemleri", "radyoloji"),
        ("x-ray bulgulari", "radyoloji"),
        ("kanal tedavisi asamalari", "endodonti"),
        ("pulpa anatomi", "endodonti"),
        ("implant ve protez planlamasi", "protez"),
        ("dis eti hastaligi gingiva", "periodontoloji"),
        ("periodontal tedavi", "periodontoloji"),
        ("histoloji doku tipleri", "histoloji"),
        ("fizyoloji homeostaz mekanizmalari", "fizyoloji"),
        ("cerrahi cekim endikasyonlari", "cerrahi"),
        ("antibiyotik farmakoloji", "farmakoloji"),
        ("cocuk dis hekimligi pedodonti", "pedodonti"),
        ("kompozit dolgu restoratif", "restoratif"),
    ])
    def test_keyword_maps_to_correct_ders(self, query: str, expected: str):
        assert _detect_ders(query) == expected

    def test_unrecognised_query_returns_none(self):
        assert _detect_ders("genel sohbet nasil gidiyor") is None

    def test_empty_string_returns_none(self):
        assert _detect_ders("") is None

    def test_case_insensitive(self):
        assert _detect_ders("PATOLOJI konusu") == "patoloji"


# ─── orchestrate_search ───────────────────────────────────────────────────────

PATCH_PINECONE = "bot.services.orchestrator.pinecone_search"
PATCH_MULTI = "bot.services.orchestrator.search_multi_ns"
PATCH_ANKI_MULTI = "bot.services.orchestrator.search_anki_multi_ns"
PATCH_QUESTIONS = "bot.services.orchestrator.search_questions"


class TestOrchestrateSearch:

    async def test_ders_calis_searches_pdfs_and_questions(self):
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]) as mock_q,
        ):
            result = await orchestrate_search("patoloji anlat", "ders_calis")

        assert mock_p.called or mock_m.called
        assert mock_q.called
        assert "brain" not in result

    async def test_hafiza_searches_brain_only(self):
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[{"text": "memory"}])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]) as mock_q,
        ):
            result = await orchestrate_search("en son ne calistim", "hafiza")

        assert mock_m.called
        assert "brain" in result
        assert mock_q.called is False

    async def test_genel_with_no_ders_searches_brain(self):
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]) as mock_q,
        ):
            result = await orchestrate_search("merhaba nasil gidiyor", "genel")

        assert mock_m.called
        assert mock_q.called is False

    async def test_forced_index_mybrain_exclusive(self):
        """forced_index=mybrain → SADECE mybrain aranır, pdfs ve questions aranmaz."""
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[{"text": "note"}])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]) as mock_q,
        ):
            result = await orchestrate_search("notlarim", "ders_calis", forced_index="mybrain")

        assert mock_m.called
        assert "brain" in result
        assert "pdfs" not in result
        assert "questions" not in result

    async def test_forced_index_myppdfs_exclusive(self):
        """forced_index=myppdfs → SADECE myppdfs aranır, brain ve questions aranmaz."""
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]) as mock_q,
        ):
            result = await orchestrate_search("genel konu", "genel", forced_index="myppdfs")

        assert mock_p.called or mock_m.called
        assert "pdfs" in result
        assert "brain" not in result
        assert "questions" not in result

    async def test_forced_index_dusbankasi_exclusive(self):
        """Kritik: forced_index=dusbankasi → SADECE soru bankası aranır (/soru komutu)."""
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[{"question": "test"}]) as mock_q,
        ):
            result = await orchestrate_search(
                "patoloji sorusu", "soru_sor", forced_index="dusbankasi"
            )

        assert mock_q.called
        assert "questions" in result
        assert "pdfs" not in result
        assert "brain" not in result
        assert mock_p.called is False
        assert mock_m.called is False

    async def test_forced_index_anki_exclusive(self):
        """forced_index=anki → SADECE Anki kartları aranır."""
        with (
            patch(PATCH_PINECONE, return_value=[{"text": "anki card"}]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]) as mock_q,
        ):
            result = await orchestrate_search(
                "protez kartlari", "ders_calis", forced_index="anki"
            )

        assert "anki" in result
        assert "pdfs" not in result
        assert "brain" not in result
        assert "questions" not in result
        assert mock_q.called is False

    async def test_forced_index_anki_unknown_ders_uses_multi_ns(self):
        """Anki: bilinmeyen branş namespace'i → tüm Anki namespace'lerinde ara."""
        with (
            patch(PATCH_PINECONE, return_value=[]) as mock_p,
            patch(PATCH_ANKI_MULTI, new=AsyncMock(return_value=[{"text": "card"}])) as mock_a,
            patch(PATCH_QUESTIONS, return_value=[]),
        ):
            result = await orchestrate_search(
                "genel bir kart ara", "ders_calis", forced_index="anki"
            )

        assert "anki" in result
        assert mock_a.called  # search_anki_multi_ns kullanıldı (tüm NS'ler)

    async def test_speed_mode_fast_with_detected_ders_uses_single_ns(self):
        with (
            patch(PATCH_PINECONE, return_value=[{"text": "hit"}]) as mock_p,
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])) as mock_m,
            patch(PATCH_QUESTIONS, return_value=[]),
        ):
            await orchestrate_search(
                "patoloji anlat", "ders_calis",
                settings={"speed_mode": "fast"}
            )

        assert mock_p.called
        assert mock_m.called is False

    async def test_search_exception_is_caught_and_returns_empty_list(self):
        with (
            patch(PATCH_PINECONE, side_effect=RuntimeError("network error")),
            patch(PATCH_MULTI, new=AsyncMock(side_effect=RuntimeError("network error"))),
            patch(PATCH_QUESTIONS, side_effect=RuntimeError("network error")),
        ):
            result = await orchestrate_search("patoloji anlat", "ders_calis")

        for key, val in result.items():
            assert val == []

    async def test_returns_dict_with_correct_keys(self):
        with (
            patch(PATCH_PINECONE, return_value=[]),
            patch(PATCH_MULTI, new=AsyncMock(return_value=[])),
            patch(PATCH_QUESTIONS, return_value=[]),
        ):
            result = await orchestrate_search("patoloji anlat", "ders_calis")

        assert isinstance(result, dict)
        assert "pdfs" in result or "questions" in result
