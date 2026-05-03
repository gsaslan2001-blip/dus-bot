import os
import sys
import time
import functools
from openai import OpenAI
from pinecone import Pinecone

# ─── OPENAI EMBEDDER ───

class OpenAIEmbedder:
    def __init__(self, model_name="text-embedding-3-large", dimensionality=3072):
        self.model_name = model_name
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            sys.stderr.write("[openai] UYARI: OPENAI_API_KEY bulunamadı.\n")
        self.client = OpenAI(api_key=api_key)
        self.dimensionality = dimensionality
        sys.stderr.write(f"[openai] OpenAI Embedder hazır ({self.model_name}, dim: {self.dimensionality}).\n")

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=[text],
            dimensions=self.dimensionality
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if not texts: return []

        all_embeddings = []
        batch_size = 500 # OpenAI için güvenli bir batch boyutu

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            sys.stderr.write(f"[openai] Batch işleniyor: {i}-{i+len(batch)} / {len(texts)}\n")

            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch,
                dimensions=self.dimensionality
            )
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

# ─── PINECONE INFERENCE EMBEDDER (E5 1024-dim, server-side) ───

class PineconeEmbedder:
    """Pinecone Inference API üzerinden embedding üretir. Yerel model gerektirmez."""
    def __init__(self, model_name="multilingual-e5-large"):
        self.model_name = model_name
        self.dimensionality = 1024
        self._pc = None  # Lazy init
        self._init_error = None
        api_key = os.environ.get("PINECONE_API_KEY")
        if api_key:
            try:
                self._pc = Pinecone(api_key=api_key)
                sys.stderr.write(f"[pinecone-embed] Pinecone Inference Embedder hazır ({self.model_name}, dim: {self.dimensionality}).\n")
            except Exception as e:
                self._init_error = str(e)
                sys.stderr.write(f"[pinecone-embed] UYARI: Pinecone client baslatilamadi: {e}\n")
        else:
            self._init_error = "PINECONE_API_KEY bulunamadı"
            sys.stderr.write("[pinecone-embed] UYARI: PINECONE_API_KEY bulunamadı.\n")

    def _ensure_client(self):
        if self._pc is None:
            raise RuntimeError(f"Pinecone embedder kullanılamıyor: {self._init_error}")

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        self._ensure_client()
        input_type = "query" if is_query else "passage"
        result = self._pc.inference.embed(
            model=self.model_name,
            inputs=[{"text": text}],
            parameters={"input_type": input_type}
        )
        return result.data[0].values

    def embed_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if not texts: return []
        self._ensure_client()
        input_type = "query" if is_query else "passage"
        all_embeddings = []
        batch_size = 100  # Pinecone inference batch limit

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            sys.stderr.write(f"[pinecone-embed] Batch işleniyor: {i}-{i+len(batch)} / {len(texts)}\n")
            inputs = [{"text": t} for t in batch]
            result = self._pc.inference.embed(
                model=self.model_name,
                inputs=inputs,
                parameters={"input_type": input_type}
            )
            all_embeddings.extend([d.values for d in result.data])

        return all_embeddings

# ─── GEMINI EMBEDDER ───

class GeminiEmbedder:
    def __init__(self, model_name="models/gemini-embedding-2"):
        import google.generativeai as genai
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._genai = genai
        self.model_name = model_name
        self.dimensionality = 1024
        sys.stderr.write(f"[gemini] Gemini Embedder hazır ({self.model_name}, dim: {self.dimensionality}).\n")

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        result = self._genai.embed_content(
            model=self.model_name,
            content=text,
            task_type=task_type,
            output_dimensionality=self.dimensionality
        )
        return result['embedding']

    def embed_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if not texts: return []
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        
        all_embeddings = []
        batch_size = 90 # Free Tier koruması
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            sys.stderr.write(f"[gemini] Batch işleniyor: {i}-{i+len(batch)} / {len(texts)}\n")
            
            try:
                result = self._genai.embed_content(
                    model=self.model_name,
                    content=batch,
                    task_type=task_type,
                    output_dimensionality=self.dimensionality
                )
                all_embeddings.extend(result['embedding'])
            except Exception as e:
                if "429" in str(e):
                    sys.stderr.write("[gemini] 429 Quota Exceeded! 65s bekleniyor...\n")
                    time.sleep(65)
                    result = self._genai.embed_content(
                        model=self.model_name,
                        content=batch,
                        task_type=task_type,
                        output_dimensionality=self.dimensionality
                    )
                    all_embeddings.extend(result['embedding'])
                else: raise e
            
            if i + batch_size < len(texts):
                time.sleep(65)
                
        return all_embeddings

@functools.lru_cache(maxsize=4)
def get_embedder(provider="pinecone", dimension=None):
    """
    Provider'a göre embedder döner.
    Varsayılan: pinecone (Pinecone Inference API, multilingual-e5-large, 1024-dim)

    Seçenekler:
      - "pinecone" → Pinecone Inference API (1024-dim), myppdfs/mybrain yükleme ve arama
      - "openai"   → OpenAI (varsayılan 3072-dim), anki indeksi için zorunlu
      - "local"    → Pinecone Inference'a yönlendirir (geriye dönük uyumluluk)
    """
    if provider in ("pinecone", "local"):
        return PineconeEmbedder()
    elif provider == "openai":
        dim = dimension if dimension else 3072
        return OpenAIEmbedder(dimensionality=dim)
    else:
        return GeminiEmbedder()

# Geriye dönük uyumluluk — yeni kodda get_embedder() kullanın
def get_local_embedder(provider="pinecone", dimension=None):
    import warnings
    warnings.warn("get_local_embedder() deprecated, get_embedder() kullanın", DeprecationWarning, stacklevel=2)
    return get_embedder(provider=provider, dimension=dimension)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("Testing OpenAI...")
    v = get_local_embedder("openai").embed_text("Test")
    print(f"OpenAI Dim: {len(v)}")
