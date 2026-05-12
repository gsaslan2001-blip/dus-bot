"""Tests for scripts/anki_parser.py — Anki card parsing functions."""
import pytest
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# clean_cloze
# ---------------------------------------------------------------------------

class TestCleanCloze:
    def setup_method(self):
        from scripts.anki_parser import clean_cloze
        self.fn = clean_cloze

    def test_simple_cloze_deletion(self):
        assert self.fn("{{c1::patoloji}}") == "patoloji"

    def test_cloze_with_hint(self):
        assert self.fn("{{c1::patoloji::ipucu}}") == "patoloji"

    def test_multiple_cloze_deletions(self):
        result = self.fn("{{c1::patoloji}} ve {{c2::radyoloji}}")
        assert result == "patoloji ve radyoloji"

    def test_numbered_cloze(self):
        assert self.fn("{{c3::tümör}}") == "tümör"

    def test_no_cloze_unchanged(self):
        assert self.fn("normal metin") == "normal metin"

    def test_empty_string_returns_empty(self):
        assert self.fn("") == ""

    def test_none_returns_empty(self):
        assert self.fn(None) == ""

    def test_cloze_in_sentence(self):
        result = self.fn("{{c1::Patoloji}} tümörü {{c2::malign}} olabilir")
        assert result == "Patoloji tümörü malign olabilir"


# ---------------------------------------------------------------------------
# clean_html
# ---------------------------------------------------------------------------

class TestCleanHtml:
    def setup_method(self):
        from scripts.anki_parser import clean_html
        self.fn = clean_html

    def test_br_tag_becomes_space(self):
        result = self.fn("satır bir<br>satır iki")
        assert "satır bir" in result
        assert "satır iki" in result
        assert "<br>" not in result

    def test_br_self_closing(self):
        result = self.fn("satır<br/>devam")
        assert "<br/>" not in result

    def test_generic_tags_removed(self):
        result = self.fn("<b>kalın</b> metin <i>italik</i>")
        assert result == "kalın metin italik"

    def test_no_html_unchanged(self):
        assert self.fn("temiz metin") == "temiz metin"

    def test_empty_string_returns_empty(self):
        assert self.fn("") == ""

    def test_none_returns_empty(self):
        assert self.fn(None) == ""

    def test_nested_tags_removed(self):
        result = self.fn("<div><span>içerik</span></div>")
        assert result == "içerik"


# ---------------------------------------------------------------------------
# clean_field
# ---------------------------------------------------------------------------

class TestCleanField:
    def setup_method(self):
        from scripts.anki_parser import clean_field
        self.fn = clean_field

    def test_strips_whitespace(self):
        assert self.fn("  metin  ") == "metin"

    def test_removes_html_and_strips(self):
        assert self.fn("  <b>metin</b>  ") == "metin"

    def test_empty_returns_empty(self):
        assert self.fn("") == ""


# ---------------------------------------------------------------------------
# parse_line  — advanced format (GUID + NoteType)
# ---------------------------------------------------------------------------

class TestParseLineAdvancedFormat:
    def setup_method(self):
        from scripts.anki_parser import parse_line, CLOZE_TYPE, BASIC_TYPE
        self.fn = parse_line
        self.CLOZE_TYPE = CLOZE_TYPE
        self.BASIC_TYPE = BASIC_TYPE

    def _cloze_line(self, guid="abc", text="{{c1::patoloji}} tümörü", baslik="Tümörler", extra=""):
        return f"{guid}\t{self.CLOZE_TYPE}\tProtez::Ünite\t{text}\t{baslik}\t{extra}"

    def _basic_line(self, guid="xyz", front="Soru nedir?", back="Cevap budur", baslik="Başlık"):
        return f"{guid}\t{self.BASIC_TYPE}\tProtez::Ünite\t{front}\t{back}\t{baslik}"

    def test_cloze_card_parsed(self):
        card = self.fn(self._cloze_line(), ders="patoloji", unite="tumor")
        assert card is not None
        assert card["kart_tipi"] == "cloze"
        assert card["guid"] == "abc"
        assert card["ders"] == "patoloji"

    def test_cloze_text_cleaned(self):
        card = self.fn(self._cloze_line(text="{{c1::patoloji}} tümörü"), ders="p", unite="u")
        assert "{{c1::" not in card["text_clean"]
        assert "patoloji" in card["text_clean"]

    def test_basic_card_parsed(self):
        card = self.fn(self._basic_line(), ders="protez", unite="morf")
        assert card is not None
        assert card["kart_tipi"] == "basic"
        assert card["front"] == "Soru nedir?"
        assert card["back"] == "Cevap budur"

    def test_basic_text_clean_combines_front_back(self):
        card = self.fn(self._basic_line(front="Soru", back="Cevap"), ders="p", unite="u")
        assert "Soru" in card["text_clean"]
        assert "Cevap" in card["text_clean"]

    def test_vektorlenecek_includes_baslik(self):
        card = self.fn(self._cloze_line(baslik="Tümörler"), ders="p", unite="u")
        assert "Tümörler" in card["vektorlenecek_metin"]

    def test_empty_cloze_text_returns_none(self):
        line = f"abc\t{self.CLOZE_TYPE}\tDeck\t\tBaşlık\t"
        card = self.fn(line, ders="p", unite="u")
        assert card is None

    def test_empty_basic_front_returns_none(self):
        line = f"abc\t{self.BASIC_TYPE}\tDeck\t\tCevap\tBaşlık"
        card = self.fn(line, ders="p", unite="u")
        assert card is None


# ---------------------------------------------------------------------------
# parse_line  — simple format (no NoteType field)
# ---------------------------------------------------------------------------

class TestParseLineSimpleFormat:
    def setup_method(self):
        from scripts.anki_parser import parse_line
        self.fn = parse_line

    def test_simple_cloze_detected(self):
        line = "{{c1::patoloji}} tümörü nedir\tBaşlık\t"
        card = self.fn(line, ders="patoloji", unite="tumor")
        assert card is not None
        assert card["kart_tipi"] == "cloze"

    def test_simple_basic_detected(self):
        line = "Soru metni\tCevap metni\tBaşlık"
        card = self.fn(line, ders="protez", unite="morf")
        assert card is not None
        assert card["kart_tipi"] == "basic"

    def test_simple_format_generates_hash_guid(self):
        line = "Soru metni\tCevap metni\tBaşlık"
        card = self.fn(line, ders="protez", unite="morf")
        assert card["guid"].startswith("hash_")


# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------

class TestParseFile:
    def setup_method(self):
        from scripts.anki_parser import parse_file, CLOZE_TYPE, BASIC_TYPE
        self.fn = parse_file
        self.CLOZE_TYPE = CLOZE_TYPE
        self.BASIC_TYPE = BASIC_TYPE

    def _write_temp_file(self, content: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False)
        tmp.write(content)
        tmp.close()
        return Path(tmp.name)

    def test_parse_multiple_cards(self):
        content = (
            f"abc\t{self.BASIC_TYPE}\tDeck\tSoru1\tCevap1\tBaşlık\n"
            f"def\t{self.BASIC_TYPE}\tDeck\tSoru2\tCevap2\tBaşlık\n"
        )
        cards = self.fn(self._write_temp_file(content), "protez", "morf")
        assert len(cards) == 2

    def test_comment_and_blank_lines_skipped(self):
        content = (
            "# Yorum satırı\n"
            "\n"
            f"abc\t{self.BASIC_TYPE}\tDeck\tSoru\tCevap\tBaşlık\n"
        )
        cards = self.fn(self._write_temp_file(content), "protez", "morf")
        assert len(cards) == 1

    def test_empty_file_returns_empty_list(self):
        cards = self.fn(self._write_temp_file("# Only comment\n"), "protez", "morf")
        assert cards == []

    def test_mixed_cloze_and_basic(self):
        content = (
            f"abc\t{self.CLOZE_TYPE}\tDeck\t{{{{c1::patoloji}}}}\tBaşlık\t\n"
            f"def\t{self.BASIC_TYPE}\tDeck\tSoru\tCevap\tBaşlık\n"
        )
        cards = self.fn(self._write_temp_file(content), "patoloji", "tumor")
        types = {c["kart_tipi"] for c in cards}
        assert "cloze" in types
        assert "basic" in types
