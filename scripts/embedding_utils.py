import os
import sys
import time
import functools
import google.generativeai as genai
from openai import OpenAI

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

# ─── LOCAL E5 EMBEDDER ───

class LocalE5Embedder:
    def __init__(self, model_name="intfloat/multilingual-e5-large"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.dimensionality = 1024
        # Modeli CPU'da başlatıyoruz (DUS Mentörü standart)
        sys.stderr.write(f"[local] {self.model_name} yükleniyor...\n")
        self.model = SentenceTransformer(self.model_name, device="cpu")
        sys.stderr.write(f"[local] Local E5 Embedder hazır (dim: {self.dimensionality}).\n")

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        prefix = "query: " if is_query else "passage: "
        vec = self.model.encode([prefix + text], normalize_embeddings=True)
        return vec[0].tolist()

    def embed_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if not texts: return []
        prefix = "query: " if is_query else "passage: "
        prefixed_texts = [prefix + t for t in texts]
        vecs = self.model.encode(prefixed_texts, normalize_embeddings=True, show_progress_bar=False)
        return vecs.tolist()

# ─── GEMINI EMBEDDER ───

class GeminiEmbedder:
    def __init__(self, model_name="models/gemini-embedding-2"):
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.dimensionality = 1024
        sys.stderr.write(f"[gemini] Gemini Embedder hazır ({self.model_name}, dim: {self.dimensionality}).\n")

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        result = genai.embed_content(
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
                result = genai.embed_content(
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
                    result = genai.embed_content(
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
def get_local_embedder(provider="openai", dimension=None):
    """
    Kullanıcı tercihine göre embedder döner. 
    Varsayılan: openai (text-embedding-3-large)
    """
    if provider == "local":
        return LocalE5Embedder()
    elif provider == "openai":
        # Eğer boyut belirtilmemişse 3072, belirtilmişse (örn 1024) onu kullan
        dim = dimension if dimension else 3072
        return OpenAIEmbedder(dimensionality=dim)
    else:
        return GeminiEmbedder()

# Geriye dönük uyumluluk
get_embedder = get_local_embedder

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("Testing OpenAI...")
    v = get_local_embedder("openai").embed_text("Test")
    print(f"OpenAI Dim: {len(v)}")
