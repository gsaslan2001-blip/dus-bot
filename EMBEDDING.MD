# 🧠 DUS Mentörü — Embedding Mimari Rehberi

> Bu dosya, projenin vektör tabanına veri işleme ve arama mimarisini açıklar.
> Son güncelleme: 2026-04-23 | v7.0 — **Tam Yerel (Local-First) Mimari**

---

## 1. Local-First Model Yapısı

Proje, bulut kotalarından bağımsız, yüksek performanslı ve gizlilik odaklı bir yerel embedding mimarisi kullanır.

| Model | Tip | Konum | Kullanım Alanı | Boyut |
|-------|-----|-------|----------------|-------|
| **Multilingual-E5-Large** | Local | CPU/GPU (Offline) | `mybrain`, `myppdfs`, `chathistory` | 1024 |
| **bge-reranker-v2-m3** | Remote | Pinecone Rerank API | Tüm Arama Sonuçlarını Sıralama | — |

> **MİMARİ DEĞİŞİKLİK:** Pinecone Inference API (Llama) kotaları aşıldığı ve yerel performans daha stabil olduğu için tüm hibrit yapı yerel E5'e taşınmıştır. Llama artık aktif akışta kullanılmamaktadır.

---

## 2. Aktif İş Akışı (myppdfs — Yerel Embedding + Uzak Arama)

> **⚠️ Pinecone bulut kotası (5M token) dolduğu için bu akış zorunludur.**

### Adım 1 — Sorgu Al
Kullanıcıdan konu başlığı veya DUS sorusu alınır (örn: "Gorlin Sendromu").

### Adım 2 — Yerel Vektörleme (Local Embedding)
`scripts/search_engine.py` altyapısı, sorguyu yerel CPU'da **Multilingual-E5-Large** modeli ile 1024 boyutlu bir vektöre dönüştürür.

```python
from embedding_utils import embedder
vec = embedder.embed_text("query: Gorlin Sendromu", is_query=True)  # 1024-dim
```

**Neden yerel?** Pinecone Inference API bulut kotası doldu → tüm embedding işlemleri offline yapılır.

### Adım 3 — Pinecone Araması (Remote Search)
Yerelde oluşturulan ham vektör, `myppdfs` indeksinin ilgili namespace(ler)ine gönderilir. Pinecone yalnızca matematiksel benzerlik (cosine similarity) hesaplayarak en ilgili 15 PDF parçasını döndürür.

```python
index = pc.Index(host="myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io")
results = index.query(vector=vec, top_k=15, namespace="patoloji", include_metadata=True)
```

### Adım 4 — Yeniden Sıralama (Reranking)
Pinecone'dan dönen 15 sonuç, `bge-reranker-v2-m3` API'sinden geçirilir. En alakalı 5–10 parça seçilir.

```python
pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query="Gorlin Sendromu",
    documents=[r["metadata"]["text"] for r in results.matches],
    top_n=5
)
```

### Adım 5 — Sentez ve Sunum
Gelen ham PDF metinleri ayıklanır ve DUS formatına (Adım 0–6 kaskadı: tablo, madde işaretleri, high-yield notlar, 5 soru) dönüştürülerek sunulur.

### Adım 6 — Hafıza Mühürleme (Staging)
Konuşulan rafine bilgiler `vektörlenecek/` klasörüne `.md` olarak kaydedilir. Kota açıldığında `mybrain` indeksine (`dus-data` namespace) kalıcı olarak yüklenir.

```
vektörlenecek/gorlin_sendromu.md  →  (ileride) mybrain / dus-data
```

---

## 4. Arama ve Uyum Protokolü

Arama sırasında, hedef indekse göre otomatik model seçimi yapılır:

- **`mybrain` Sorgusu:** Llama ile vektörlenir (Eğer kota doluysa Yerel E5'e fallback yapar).
- **`myppdfs` Sorgusu:** Yerel E5 ile vektörlenir (Hassasiyet için zorunlu).

### Reranker (Zorunlu)
Vektör aramasından dönen sonuçlar her zaman `bge-reranker-v2-m3` (Pinecone Rerank API) üzerinden geçirilerek en alakalı 5 parça seçilir.

---

## 5. Local-First Kayıt Stratejisi

Bulut kotaları (5M token/ay) dolduğunda veya çevrimdışı çalışma gerektirdiğinde şu protokol izlenir:

1. **Staging:** Veriler `vektörlenecek/` klasörüne `.md` olarak kaydedilir.
2. **Local Processing:** PDF'ler `upload_pdf_local.py` ile yerelde işlenir.
3. **Delayed Sync:** Kota açıldığında `master_upload.py` ile tüm yerel veriler Pinecone'a senkronize edilir.

---

## 6. Dosya Referansları

- `scripts/embedding_utils.py`: Hibrit model sınıflarını (Llama + E5) içerir.
- `scripts/search_engine.py`: Reranker ve çoklu indeks tarama mantığını içerir.
- `scripts/upload_pdf_local.py`: PDF'leri yerel E5 ile işleyen araçtır.

---
*v6.2 | 2026-04-23 | DUS Mentörü Teknik Ekibi*
