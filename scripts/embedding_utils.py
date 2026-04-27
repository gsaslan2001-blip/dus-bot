import os
import sys
import torch
import functools
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Force offline settings for local model
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Snapshot path for Local E5
_E5_SNAPSHOT = (
    r"C:\Users\FURKAN\.cache\huggingface\hub"
    r"\models--intfloat--multilingual-e5-large"
    r"\snapshots\3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3"
)

# Import config
sys.path.insert(0, os.path.dirname(__file__))
try:
    from config import PINECONE_API_KEY
except ImportError:
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")

# ─── LLAMA EMBEDDER (CLOUDBASED - WITH AUTOMATIC LOCAL FALLBACK) ───

class PineconeLlamaEmbedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.pc = Pinecone(api_key=PINECONE_API_KEY)
            sys.stderr.write("[embedder] Pinecone Llama-v2 (Integrated Inference) aktif.\n")
        return cls._instance

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        try:
            input_type = "query" if is_query else "passage"
            res = self.pc.inference.embed(
                model="llama-text-embed-v2",
                inputs=[text],
                parameters={"input_type": input_type}
            )
            return res[0].values
        except Exception as e:
            sys.stderr.write(f"[embedder] Llama hatasi, Yerel E5'e geciliyor: {e}\n")
            return get_local_embedder().embed_text(text, is_query=is_query)

    def embed_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if not texts: return []
        try:
            input_type = "query" if is_query else "passage"
            res = self.pc.inference.embed(
                model="llama-text-embed-v2",
                inputs=texts,
                parameters={"input_type": input_type}
            )
            return [record.values for record in res]
        except Exception as e:
            sys.stderr.write(f"[embedder] Llama batch hatasi, Yerel E5'e geciliyor: {e}\n")
            return get_local_embedder().embed_batch(texts, is_query=is_query)

# ─── LOCAL E5 EMBEDDER (CPU/GPU BASED - SENTENCE TRANSFORMERS) ───

class LocalE5Embedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        sys.stderr.write(f"[embedder] Local Multilingual-E5-Large yukleniyor ({device})...\n")
        self.model = SentenceTransformer(_E5_SNAPSHOT, device=device, local_files_only=True)
        sys.stderr.write("[embedder] Yerel model hazir.\n")

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        prefix = "query: " if is_query else "passage: "
        text = f"{prefix}{text}" if not text.startswith(prefix) else text
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()

    def embed_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if not texts: return []
        prefix = "query: " if is_query else "passage: "
        prefixed = [t if t.startswith(prefix) else f"{prefix}{t}" for t in texts]
        return self.model.encode(prefixed, normalize_embeddings=True).tolist()

@functools.lru_cache(maxsize=1)
def get_embedder():
    """Lazy getter for PineconeLlamaEmbedder"""
    return PineconeLlamaEmbedder()

@functools.lru_cache(maxsize=1)
def get_local_embedder():
    """Lazy getter for LocalE5Embedder"""
    return LocalE5Embedder()

# --- Module-level Singletons (Backwards Compatibility) ---
embedder = get_embedder()
local_embedder = get_local_embedder()

if __name__ == "__main__":
    # Test Llama
    print("Testing Llama (Lazy Loading)...")
    v1 = get_embedder().embed_text("Test bulut")
    print(f"Llama OK. Dim: {len(v1)}")
    
    # Test Local E5
    print("\nTesting Local E5 (Lazy Loading)...")
    v2 = get_local_embedder().embed_text("Test yerel")
    print(f"Local E5 OK. Dim: {len(v2)}")
