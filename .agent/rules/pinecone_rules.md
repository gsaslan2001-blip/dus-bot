# Pinecone Operasyon Kuralları — DUS Mentörü

> Pinecone index'lerini kullanırken her zaman bu kuralları uygula.

## 1. Index Envanteri (Hızlı Referans)

| Index | Host | Model | Not |
|-------|------|-------|-----|
| `mybrain` | `mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io` | YEREL E5 | **LE+S5 Modu** |
| `myppdfs` | `myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io` | YEREL E5 | **LE+S5 Modu** |
| `dusbankasi` | `dusbankasi-0crkhvy.svc.aped-4627-b74a.pinecone.io` | OpenAI ada-3-small | Manuel embed |

## 2. Arama Protokolü

### Yerel E5 ile Arama (mybrain, myppdfs):
```python
from embedding_utils import embedder

# 1. Sorguyu yerel CPU'da vektörle
query_vec = embedder.embed_text("neoplazi sınıflaması", is_query=True)

# 2. Vektör ile Pinecone'u sorgula
results = index.query(
    namespace="patoloji",
    vector=query_vec,
    top_k=20,
    include_metadata=True
)

# 3. Ardından rerank:
reranked = pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query="neoplazi sınıflaması",
    documents=[r["metadata"]["text"] for r in results["matches"]],
    top_n=5
)
```

### Dusbankasi (Manuel Embed):
```python
# Önce OpenAI ile embedding üret
embedding = openai_client.embeddings.create(
    input=query,
    model="text-embedding-3-small"
).data[0].embedding
# Sonra Pinecone'a gönder
results = index.query(vector=embedding, top_k=10, include_metadata=True)
```

## 3. Namespace Haritası

### mybrain:
- `dus-data` → DUS müfredat + mimari kararlar + oturum logları
- `claude_memory` → AI proje belleği, PRD dosyaları

### myppdfs:
- `patoloji` → 680 vektör
- `endodonti` → 705 vektör
- `radyoloji` → 2.700 vektör
- `protez` → 1.000 vektör
- `histoloji` → 433 vektör
- `fizyoloji` → 466 vektör
- `periodontoloji` → 3.621 vektör

## 4. Hafıza Kaydetme Formatı

```python
from embedding_utils import embedder

# Yerel vektör üret
vec = embedder.embed_text("<içerik>", is_query=False)

record = {
    "id": "session_log-YYYY-MM-DD-HHMM",
    "values": vec,
    "metadata": {
        "text": "<içerik>",
        "source": "antigravity_session",
        "type": "session_log",
        "date": "YYYY-MM-DD"
    }
}
index.upsert(vectors=[record], namespace="dus-data")
```

## 5. Kritik Uyumsuzluk Notu

`dusbankasi` index'i `__default__` namespace API uyumsuzluğuna sahip:
- `search_records` MCP tool'u çalışmaz
- `query()` metodunu doğrudan kullan
- Embedding önce OpenAI ile üretilmeli
