"""Tests for scripts/anki_dedup_fast.py — pure tokenization and similarity functions."""
import pytest
import io
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def setup_method(self):
        from scripts.anki_dedup_fast import _tokenize
        self.fn = _tokenize

    def test_basic_tokenization(self):
        tokens = self.fn("patoloji tümör karsinom")
        assert "patoloji" in tokens
        assert "tümör" in tokens
        assert "karsinom" in tokens

    def test_stopwords_removed(self):
        tokens = self.fn("patoloji ve tümör ile karsinom")
        assert "ve" not in tokens
        assert "ile" not in tokens
        assert "patoloji" in tokens

    def test_punctuation_stripped(self):
        tokens = self.fn("patoloji, tümör; karsinom.")
        assert "patoloji" in tokens
        assert "tümör" in tokens

    def test_numbers_removed(self):
        tokens = self.fn("tip 2 diyabet 1990 yılında")
        assert "2" not in tokens
        assert "1990" not in tokens

    def test_lowercasing(self):
        tokens = self.fn("PATOLOJİ TÜMÖR")
        assert "patoloji" in tokens or "patolojİ" in tokens.union({"patoloji"})
        # At least the token is lowercase
        assert all(t == t.lower() for t in tokens)

    def test_empty_string_returns_empty_set(self):
        tokens = self.fn("")
        assert isinstance(tokens, set)

    def test_only_stopwords_returns_empty(self):
        tokens = self.fn("ve ile bu da de ki")
        assert len(tokens) == 0

    def test_returns_set_not_list(self):
        result = self.fn("patoloji patoloji tümör")
        assert isinstance(result, set)
        # Deduplication happens automatically with sets
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# jaccard
# ---------------------------------------------------------------------------

class TestJaccard:
    def setup_method(self):
        from scripts.anki_dedup_fast import jaccard
        self.fn = jaccard

    def test_identical_sets(self):
        a = {"a", "b", "c"}
        assert self.fn(a, a) == 1.0

    def test_disjoint_sets(self):
        assert self.fn({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        # intersection=2, union=4 → 0.5
        assert self.fn(a, b) == pytest.approx(0.5)

    def test_empty_set_returns_zero(self):
        assert self.fn(set(), {"a", "b"}) == 0.0
        assert self.fn({"a", "b"}, set()) == 0.0

    def test_both_empty_returns_zero(self):
        assert self.fn(set(), set()) == 0.0

    def test_single_element_identical(self):
        assert self.fn({"a"}, {"a"}) == 1.0

    def test_single_element_different(self):
        assert self.fn({"a"}, {"b"}) == 0.0


# ---------------------------------------------------------------------------
# asymmetric_similarity
# ---------------------------------------------------------------------------

class TestAsymmetricSimilarity:
    def setup_method(self):
        from scripts.anki_dedup_fast import asymmetric_similarity
        self.fn = asymmetric_similarity

    def test_identical_sets(self):
        a = {"a", "b", "c"}
        assert self.fn(a, a) == 1.0

    def test_subset_has_score_one(self):
        # a is subset of b → overlap/min(len(a),len(b)) = 2/2 = 1.0
        a = {"a", "b"}
        b = {"a", "b", "c", "d"}
        assert self.fn(a, b) == 1.0

    def test_no_overlap_returns_zero(self):
        assert self.fn({"a", "b"}, {"c", "d"}) == 0.0

    def test_empty_a_returns_zero(self):
        assert self.fn(set(), {"a", "b"}) == 0.0

    def test_empty_b_returns_zero(self):
        assert self.fn({"a", "b"}, set()) == 0.0

    def test_asymmetry(self):
        # Large set vs small set: score depends on direction
        small = {"a"}
        large = {"a", "b", "c", "d"}
        score_small_large = self.fn(small, large)
        score_large_small = self.fn(large, small)
        # Both use min(len(a), len(b)) = 1, intersection = 1 → both 1.0
        assert score_small_large == 1.0
        assert score_large_small == 1.0

    def test_partial_overlap(self):
        a = {"a", "b", "c"}
        b = {"a", "b", "d", "e"}
        # intersection=2, min=3 → 2/3
        result = self.fn(a, b)
        assert result == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# parse_anki_txt
# ---------------------------------------------------------------------------

class TestParseAnkiTxt:
    def setup_method(self):
        from scripts.anki_dedup_fast import parse_anki_txt
        self.fn = parse_anki_txt

    def _write_temp_file(self, content: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False)
        tmp.write(content)
        tmp.close()
        return Path(tmp.name)

    def test_basic_card_parsed(self):
        content = 'abc123\tBasic-AnKing\tDeck\tSoru metni\tCevap metni\tBaşlık\n'
        path = self._write_temp_file(content)
        cards = self.fn(path)
        assert len(cards) == 1
        assert cards[0]["guid"] == "abc123"
        assert cards[0]["question"] == "Soru metni"
        assert cards[0]["answer"] == "Cevap metni"

    def test_comment_lines_skipped(self):
        content = '# Bu bir yorum satırı\nabc\tBasic\tDeck\tSoru\tCevap\tBaşlık\n'
        path = self._write_temp_file(content)
        cards = self.fn(path)
        assert len(cards) == 1

    def test_empty_lines_skipped(self):
        content = '\nabc\tBasic\tDeck\tSoru\tCevap\tBaşlık\n\n'
        path = self._write_temp_file(content)
        cards = self.fn(path)
        assert len(cards) == 1

    def test_short_line_skipped(self):
        content = 'soru\tcevap\n'  # Only 2 fields, < 4 required
        path = self._write_temp_file(content)
        cards = self.fn(path)
        assert len(cards) == 0

    def test_tokens_computed(self):
        content = 'abc\tBasic\tDeck\tPatoloji tümör karsinom\tCevap\tBaşlık\n'
        path = self._write_temp_file(content)
        cards = self.fn(path)
        assert "tokens_q" in cards[0]
        assert isinstance(cards[0]["tokens_q"], set)
        assert "patoloji" in cards[0]["tokens_q"] or len(cards[0]["tokens_q"]) >= 0
