# Pinecone Operasyon Kuralları — DUS Mentörü

> Pinecone index'lerini kullanırken her zaman bu kuralları uygula.
> Son güncelleme: 2026-04-28 | v3.0 — Bulut Embedding Kotası Doldu, MCP search-records YASAKLANDI

---

## 🔴 KRİTİK: BULUT EMBEDDİNG KOTASI DOLDU

> **Pinecone Integrated Inference (multilingual-e5-large) bulut embedding kotası (5M token/ay) DOLMUŞTUR.**
> Bu durum `mybrain` ve `myppdfs` indekslerini etkiler.
>
> **SONUÇ:** Aşağıdaki yöntemler **429 RESOURCE_EXHAUSTED** hatası verir ve KESİNLİKLE YASAKLANMIŞTIR:
>
> | Yasak Yöntem | Neden |
> |-------------|-------|
> | `mcp_pinecone-mcp-server_search-records` | `inputs.text` parametresi bulut embedding tetikler |
> | `mcp_pinecone-mcp-server_cascading-search` | Aynı nedenle bulut embedding tetikler |
> | `index.search(query={"inputs": {"text": "..."}})` | Python SDK integrated inference — bulut embedding |
>
> **ZORUNLU ALTERNATİF:** Tüm aramalar **yerel E5-Large** modeli ile vektörleme + `index.query(vector=[...])` ile yapılır.

---

## 1. Index Envanteri (Hızlı Referans)

| Index | Host | Model | Not |
|-------|------|-------|-----|
| `mybrain` | `mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io` | YEREL E5 | Ham vektör ile `query()` kullan |
| `myppdfs` | `myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io` | YEREL E5 | Ham vektör ile `query()` kullan |
| `dusbankasi` | `dusbankasi-0crkhvy.svc.aped-4627-b74a.pinecone.io` | OpenAI ada-3-small | Manuel embed + `query()` kullan |

## 2. Arama Protokolü

### TEK GEÇERLİ YOL: Yerel E5 → Ham Vektör → query() → Rerank

```python
from embedding_utils import get_local_embedder

# 1. Sorguyu YEREL CPU/GPU'da vektörle
query_vec = get_local_embedder().embed_text("neoplazi sınıflaması", is_query=True)

# 2. Ham vektör ile Pinecone'u sorgula (BULUT EMBEDDİNG YOK)
results = index.query(
    namespace="patoloji",
    vector=query_vec,
    top_k=15,
    include_metadata=True
)

# 3. Ardından rerank (Bu İZİNLİDİR — bulut embedding kullanmaz):
reranked = pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query="neoplazi sınıflaması",
    documents=[r["metadata"]["text"] for r in results["matches"]],
    top_n=5
)
```

### Çoklu Namespace Araması:
```python
from search_engine import search_multi_ns
# search_multi_ns zaten yerel E5 kullanır ve rerank yapar
results = await search_multi_ns("konu", "myppdfs", ["radyoloji", "patoloji"], top_k=15, rerank_top_n=5)
```

### Dusbankasi (Manuel Embed — Ayrı Akış):
```python
# Önce OpenAI ile embedding üret
embedding = openai_client.embeddings.create(
    input=query,
    model="text-embedding-3-small"
).data[0].embedding
# Sonra Pinecone'a gönder
results = index.query(vector=embedding, top_k=10, include_metadata=True)
```

## 3. İzin Verilen ve Yasaklanan MCP Araçları

| MCP Aracı | Durum | Neden |
|-----------|-------|-------|
| `search-records` | ❌ YASAK | Bulut embedding tetikler |
| `cascading-search` | ❌ YASAK | Bulut embedding tetikler |
| `rerank-documents` | ✅ İZİNLİ | Embedding kullanmaz |
| `upsert-records` | ✅ İZİNLİ | Yazma işlemi, yerel vektörle kullanılır |
| `describe-index-stats` | ✅ İZİNLİ | Sadece istatistik |
| `list-indexes` | ✅ İZİNLİ | Sadece listeleme |

## 4. Namespace Haritası

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

## 5. Hafıza Kaydetme Formatı

```python
from embedding_utils import get_local_embedder

# Yerel vektör üret
vec = get_local_embedder().embed_text("<içerik>", is_query=False)

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

## 6. Kritik Uyumsuzluk Notu

`dusbankasi` index'i `__default__` namespace API uyumsuzluğuna sahip:
- `search_records` MCP tool'u çalışmaz
- `query()` metodunu doğrudan kullan
- Embedding önce OpenAI ile üretilmeli

---

*Pinecone Kuralları v3.0 | 2026-04-28 | Bulut Kotası DOLU — Tüm arama YEREL E5 ile yapılır*
