# MYBRAIN — Furkan'ın Uzun Vadeli Hafıza İndeksi

> **Bu dosya bir LLM bağlam kılavuzudur.** `mybrain` Pinecone indeksini, namespace yapısını ve bellek kullanım protokollerini tanımlar.
> Son güncelleme: 2026-04-23 | v3.0 — **Tam Yerel (Local-First) Mimari**: Tüm süreçler E5-Large ile yerelleştirildi.

---

## 1. İndeks Kimliği

| Özellik | Değer |
|---------|-------|
| **İndeks Adı** | `mybrain` |
| **Host** | `mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io` |
| **Embedding Modeli** | **YEREL (Multilingual-E5-Large)** |
| **Boyut** | 1024 |
| **Metrik** | Cosine |
| **Tür** | Serverless, AWS us-east-1 |

> **MİMARİ KARAR:** Pinecone Inference API (Llama) kotalarından ve ağ gecikmesinden bağımsızlık için tüm bellek yazma/okuma işlemleri yerel E5 modeli ile yapılır. Llama tabanlı eski kayıtlar, yeni E5 vektörleriyle kademeli olarak güncellenmektedir.

---

## 2. Namespace Envanteri

### `dus-curriculum` / `dus-memory` / `dus-progress` / `dus-strategy` / `dus-reference`
**Kaynak:** `C:\Users\FURKAN\.claude\DUS\`
**Yükleme:** `python scripts/auto_sync_dus.py`
**İçerik:** DUS müfredatı, çalışma notları, ilerleme, strateji ve akademik referanslar.

### `telos` — Kişisel Hedefler ve TELOS
**Kaynak:** `C:\Users\FURKAN\.claude\PAI\USER\TELOS`
**Yükleme:** `python scripts/dus_uploader.py --telos`
**İçerik:** Furkan'ın kişisel hedefleri ve vizyonu.

### `chathistory` — Sohbet Geçmişi ve Notlar
**Kaynak:** `vektörlenecek/` (Lokal staging)
**Yükleme:** `python scripts/dus_uploader.py --chathistory`
**İçerik:** Seans bazlı tam konuşma dökümleri ve rafine çalışma notları.

### `claude_memory` — AI Asistan Proje Belleği (Arşivsel)
**Kaynak:** `.claude/` kök ve alt dizinleri.
**İçerik:** Agent tanımları, kullanıcı tercihleri ve eski proje kararları.

---

## 3. Arama Protokolü

### Bot fonksiyonlarıyla arama:
```python
# DUS ders belleği:
search_memory("patoloji oral melanotik makül")

# Proje belleği:
search_project_memory("didikle pipeline mimari")
search_project_memory("embedding model offline kurulum")
```

### Direkt Pinecone sorgusu (yerel embed ile):
```python
from embedding_utils import embedder
from pinecone import Pinecone
import os

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(host="mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io")

query_vec = embedder.embed_text("sorgu metni", is_query=True)
results = index.query(
    vector=query_vec,
    top_k=10,
    namespace="dus-data",       # veya "claude_memory"
    include_metadata=True
)
for match in results["matches"]:
    print(match["score"], match["metadata"]["text"][:100])
```

### Reranker ile (tüm Pinecone aramalarında zorunlu):
```python
from pinecone import Pinecone

reranked = pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query="sorgu",
    documents=[m["metadata"]["text"] for m in results["matches"]],
    top_n=5,
)
```

---

## 4. Upload Workflow (Güncel)

1. Dosyayı ilgili dizine kaydet (`.claude/DUS`, `TELOS` veya `vektörlenecek/`).
2. Senkronizasyon komutunu çalıştır:
   ```bash
   # Otomatik tam senkronizasyon (Önerilen):
   python scripts/auto_sync_dus.py

   # Manuel branş bazlı güncelleme:
   python scripts/dus_uploader.py --telos
   python scripts/dus_uploader.py --chathistory
   ```
3. **Akıllı Güncelleme:** `dus_uploader.py` manifest dosyasını kontrol eder. Sadece içeriği değişen dosyaları siler ve yeniden yükler. Kota dostudur.

---

## 5. Hafıza Kaydetme Politikası

### Otomatik Kayıt Tetikleyiciler

| Tetikleyici | Ne Kaydedilir | Namespace |
|-------------|---------------|-----------|
| Önemli mimari karar | Karar + gerekçe | `dus-data` |
| Teknik sorun çözümü | Sorun, çözüm, kod | `dus-data` |
| Yeni branş yüklendi | Tarih, chunk sayısı | `dus-data` |
| Sohbet sonu | Oturum özeti | `dus-data` |
| `remember_fact()` çağrısı | Tek kritik bilgi | `dus-data` |

### "Konuştuklarımızı Kaydet" Komutu (Local-First)

1. Tüm sohbet metnini birleştir ve formatla.
2. `vektörlenecek/` klasörüne `chat_ID_TIMESTAMP.md` olarak kaydet.
3. Eş zamanlı olarak Pinecone `chathistory`'ye upsert dene (Llama/E5 fallback ile).

### Ne Kaydedilmez?
- Gündelik selamlama/vedalar
- Pinecone API test sonuçları
- Zaten `claude_memory` içinde olan tekrar bilgiler

---

## 6. Ebbinghaus Tekrar Entegrasyonu

`claude_memory` namespace'indeki `TICKTICK_REVIEW_SYSTEM.md` dosyasına göre tekrar zaman dilimleri:

| Tekrar | Zaman |
|--------|-------|
| T+1 | 1 gün sonra |
| T+3 | 3 gün sonra |
| T+7 | 7 gün sonra |
| T+15 | 15 gün sonra |
| T+30 | 30 gün sonra |

`mybrain/dus-data`'ya "çalışılan konu" + "tarih" kaydederek bu sistemi aktive et.

---

*Proje: DUS Mentörü | İndeks: mybrain | v2.0 | 2026-04-23*
