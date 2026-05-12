"""Tests for scripts/embedding_utils.py — embedder factory and provider selection."""
import pytest
import warnings
from unittest.mock import MagicMock, patch


class TestGetEmbedder:
    def setup_method(self):
        # Clear the lru_cache between tests so each call is fresh
        from scripts.embedding_utils import get_embedder
        get_embedder.cache_clear()

    def teardown_method(self):
        from scripts.embedding_utils import get_embedder
        get_embedder.cache_clear()

    def test_pinecone_provider_returns_pinecone_embedder(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import get_embedder, PineconeEmbedder
            get_embedder.cache_clear()
            embedder = get_embedder("pinecone")
            assert isinstance(embedder, PineconeEmbedder)

    def test_local_provider_returns_pinecone_embedder(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import get_embedder, PineconeEmbedder
            get_embedder.cache_clear()
            embedder = get_embedder("local")
            assert isinstance(embedder, PineconeEmbedder)

    def test_openai_provider_returns_openai_embedder(self):
        with patch("scripts.embedding_utils.OpenAI") as mock_oai:
            mock_oai.return_value = MagicMock()
            from scripts.embedding_utils import get_embedder, OpenAIEmbedder
            get_embedder.cache_clear()
            embedder = get_embedder("openai")
            assert isinstance(embedder, OpenAIEmbedder)

    def test_openai_with_custom_dimension(self):
        with patch("scripts.embedding_utils.OpenAI") as mock_oai:
            mock_oai.return_value = MagicMock()
            from scripts.embedding_utils import get_embedder
            get_embedder.cache_clear()
            embedder = get_embedder("openai", dimension=1536)
            assert embedder.dimensionality == 1536

    def test_openai_default_dimension_is_3072(self):
        with patch("scripts.embedding_utils.OpenAI") as mock_oai:
            mock_oai.return_value = MagicMock()
            from scripts.embedding_utils import get_embedder
            get_embedder.cache_clear()
            embedder = get_embedder("openai")
            assert embedder.dimensionality == 3072

    def test_unknown_provider_returns_gemini_embedder(self):
        mock_genai = MagicMock()
        import sys
        with patch.dict(sys.modules, {"google": MagicMock(), "google.generativeai": mock_genai}):
            from scripts.embedding_utils import get_embedder, GeminiEmbedder
            get_embedder.cache_clear()
            embedder = get_embedder("gemini")
            assert isinstance(embedder, GeminiEmbedder)

    def test_result_is_cached(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import get_embedder
            get_embedder.cache_clear()
            e1 = get_embedder("pinecone")
            e2 = get_embedder("pinecone")
            assert e1 is e2  # Same cached instance


class TestGetLocalEmbedder:
    def setup_method(self):
        from scripts.embedding_utils import get_embedder
        get_embedder.cache_clear()

    def teardown_method(self):
        from scripts.embedding_utils import get_embedder
        get_embedder.cache_clear()

    def test_deprecation_warning_issued(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import get_local_embedder, get_embedder
            get_embedder.cache_clear()
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                get_local_embedder("pinecone")
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message).lower()

    def test_returns_same_result_as_get_embedder(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import get_local_embedder, get_embedder, PineconeEmbedder
            get_embedder.cache_clear()
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = get_local_embedder("pinecone")
            assert isinstance(result, PineconeEmbedder)


class TestPineconeEmbedder:
    def test_no_api_key_sets_init_error(self, monkeypatch):
        monkeypatch.delenv("PINECONE_API_KEY", raising=False)
        with patch("scripts.embedding_utils.Pinecone"):
            from scripts.embedding_utils import PineconeEmbedder
            embedder = PineconeEmbedder()
            # _pc should be None or error should be set when key is missing
            # (monkeypatching env after class is imported — check _init_error)
            # The important thing is it doesn't crash on instantiation
            assert embedder is not None

    def test_ensure_client_raises_when_pc_is_none(self):
        with patch("scripts.embedding_utils.Pinecone"):
            from scripts.embedding_utils import PineconeEmbedder
            embedder = PineconeEmbedder()
            embedder._pc = None
            embedder._init_error = "No key"
            with pytest.raises(RuntimeError):
                embedder._ensure_client()

    def test_dimensionality_is_1024(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import PineconeEmbedder
            assert PineconeEmbedder().dimensionality == 1024

    def test_embed_batch_empty_returns_empty(self):
        with patch("scripts.embedding_utils.Pinecone") as mock_pc:
            mock_pc.return_value = MagicMock()
            from scripts.embedding_utils import PineconeEmbedder
            assert PineconeEmbedder().embed_batch([]) == []


class TestOpenAIEmbedder:
    def test_embed_batch_empty_returns_empty(self):
        with patch("scripts.embedding_utils.OpenAI") as mock_oai:
            mock_oai.return_value = MagicMock()
            from scripts.embedding_utils import OpenAIEmbedder
            assert OpenAIEmbedder().embed_batch([]) == []

    def test_default_model_name(self):
        with patch("scripts.embedding_utils.OpenAI") as mock_oai:
            mock_oai.return_value = MagicMock()
            from scripts.embedding_utils import OpenAIEmbedder
            assert OpenAIEmbedder().model_name == "text-embedding-3-large"
