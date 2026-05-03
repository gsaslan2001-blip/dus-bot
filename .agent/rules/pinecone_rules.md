# Pinecone Operasyon Kuralları — DUS Mentörü

> Pinecone index'lerini kullanırken her zaman bu kuralları uygula.
> Son güncelleme: 2026-05-03 | v5.0 — Pinecone-First Mimari: Yerel embedding tamamen kaldırıldı, Pinecone Inference API + OpenAI

---

## 🟢 ARAMA VE YÜKLEME MİMARİSİ (Güncel v5.0)

| İndeks | Arama (Query) | Yükleme (Upsert) | Model | Boyut |
|---|---|---|---|---|
| `myppdfs` | **Integrated Inference** | **Pinecone Inference API** | `multilingual-e5-large` | 1024 |
| `mybrain` | **Integrated Inference** | **Pinecone Inference API** | `multilingual-e5-large` | 1024 |
| `dusbankasi` | **OpenAI embed + query()** | **OpenAI embed + upsert()** | `text-embedding-3-small` | 1536 |
| `anki` | **OpenAI embed + query()** | **OpenAI embed + upsert()** | `text-embedding-3-large` | 3072 |

### Arama Protokolü (myppdfs / mybrain)

**BİRİNCİL YÖNTEM — Integrated Inference:**
Sorgu Pinecone'a direkt gönderilir, vektörlemeyi Pinecone yapar. Hızlıdır (500ms altı).

```python
results = index.search(
    namespace="patoloji",
    query={"inputs": {"text": "neoplazi sınıflaması"}},
    top_k=15
)
```

**Rerank her aramada ZORUNLU:**
```python
reranked = pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query="<orijinal sorgu>",
    documents=[r["metadata"]["text"] for r in results["matches"]],
    top_n=5
)
```

### Yükleme Protokolü (myppdfs / mybrain)

Yüklemede Pinecone Inference API kullanılır (yerel model gerektirmez):
```python
from embedding_utils import get_embedder
vec = get_embedder("pinecone").embed_text("<içerik>", is_query=False)
index.upsert(vectors=[{"id": "...", "values": vec, "metadata": {...}}], namespace="...")
```

### dusbankasi Protokolü

OpenAI `text-embedding-3-small` (1536-dim) ile embedding üretilir, Pinecone'a gönderilir:
```python
embedding = openai_client.embeddings.create(
    input=query, model="text-embedding-3-small"
).data[0].embedding
results = index.query(vector=embedding, top_k=10, include_metadata=True)
```

### Çoklu Namespace Araması:
```python
from search_engine import search_multi_ns
results = await search_multi_ns("konu", "myppdfs", ["radyoloji", "patoloji"], top_k=15, rerank_top_n=5)
```


## 1. İzin Verilen MCP Araçları

| MCP Aracı | Durum | Neden |
|-----------|-------|-------|
| `search-records` | ✅ İZİNLİ | Integrated Inference — myppdfs/mybrain araması |
| `cascading-search` | ✅ İZİNLİ | Çoklu namespace paralel arama |
| `rerank-documents` | ✅ İZİNLİ | Embedding kullanmaz, her aramada zorunlu |
| `upsert-records` | ✅ İZİNLİ | Yazma işlemi, yerel vektörle kullanılır |
| `describe-index-stats` | ✅ İZİNLİ | Sadece istatistik |
| `list-indexes` | ✅ İZİNLİ | Sadece listeleme | |

## 2. Namespace Haritası

### mybrain:
- `dus-curriculum` → DUS müfredat akışı
- `dus-memory` → Akademik çalışma belleği
- `dus-progress` → İlerleme ve tamamlananlar
- `dus-strategy` → Strateji ve planlama
- `dus-reference` → Akademik referanslar
- `telos` → Kişisel hedefler ve TELOS
- `chathistory` → Sohbet geçmişi (synced)

### myppdfs:
- `patoloji` → 680 vektör
- `endodonti` → 705 vektör
- `radyoloji` → 2.700 vektör
- `protez` → 1.000 vektör
- `histoloji` → 433 vektör
- `fizyoloji` → 498 vektör
- `periodontoloji` → 3.621 vektör
- `cerrahi` → 589 vektör
- `farmakoloji` → 517 vektör
- `pedodonti` → 1.075 vektör
- `cikmis` → 1.560 vektör

## 3. Hafıza Kaydetme Formatı

```python
from embedding_utils import get_embedder

# Yerel vektör üret
vec = get_embedder("local").embed_text("<içerik>", is_query=False)

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
index.upsert(vectors=[record], namespace="chathistory")
```

## 4. Kritik Uyumsuzluk Notu

`dusbankasi` index'i `__default__` namespace API uyumsuzluğuna sahip:
- `search_records` MCP tool'u çalışmaz
- `query()` metodunu doğrudan kullan
- Embedding önce OpenAI `text-embedding-3-small` ile üretilmeli

---

*Pinecone Kuralları v4.0 | 2026-05-03 | Hibrit Mimari: Integrated Inference + Yerel E5 + OpenAI*
