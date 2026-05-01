# 🚀 OpenAI Vektör ve Analiz Altyapısı (DUS Mentörü)

Bu belge, DUS Mentörü projesinde kullanılan yüksek performanslı OpenAI tabanlı embedding ve analiz altyapısını açıklar.

## 1. Temel Bileşenler

| Görev | Model | Detay |
|-------|-------|-------|
| **Embedding** | `text-embedding-3-large` | 3072 Boyut, Maksimum Keskinlik |
| **LLM Judge** | `gpt-4o-mini` | Akıllı Tekilleştirme ve Pedagojik Karar Mekanizması |
| **Orchestrator** | `scripts/embedding_utils.py` | Sağlayıcı bağımsız (OpenAI/Gemini/E5) soyutlama katmanı |

## 2. Neden OpenAI `text-embedding-3-large`?

Eski sistemdeki Gemini ve Yerel E5 modellerinden bu modele geçiş yapılmasının temel nedenleri:
1. **Yüksek Boyut (3072):** 1024 boyutlu modellere göre tıbbi terimler arasındaki anlamsal farkları (örn: *Tip 1 vs Tip 2 Diyabet*) çok daha keskin ayırır.
2. **Hız ve Kota:** OpenAI'ın yüksek rate-limitleri sayesinde 13.000 kartlık setler dakikalar içinde vektörlenebilir.
3. **Tutarlılık:** "Basic" ve "Cloze" kartları arasındaki benzerlikleri yakalamada %98+ başarı oranı.

## 3. Akıllı Tekilleştirme İş Akışı (Smart Dedup)

Sistem 3 aşamalı bir huni (funnel) mantığıyla çalışır:

1. **Vektör Taraması (OpenAI Embedder):** 
   - Tüm kartlar 3072 boyutlu uzaya aktarılır.
   - Kosinüs benzerliği hesaplanır (Eşik: **0.94**).
2. **Lexical Guard (Kural Tabanlı):**
   - Vektör olarak benzeyen ancak zıt anlamlı (Anterior/Posterior, Tip 1/2 vb.) kartlar elenir.
3. **LLM Judge (gpt-4o-mini):**
   - Kalan şüpheli çiftler LLM'e gönderilir.
   - LLM, kartların pedagojik olarak aynı bilgiyi mi test ettiğine karar verir.

## 4. Kullanım (Geliştiriciler İçin)

### Vektörleme Başlatma
```python
from scripts.embedding_utils import get_local_embedder

# OpenAI embedder'ı çağır
embedder = get_local_embedder("openai")
vectors = embedder.embed_batch(["Tıp terimi 1", "Tıp terimi 2"])
```

### Akıllı Tekilleştirme Scripti
```bash
python scripts/anki_dedup_smart.py
```

## 5. Önemli Notlar
- `.env` dosyasında `OPENAI_API_KEY` tanımlı olmalıdır.
- Büyük dosyalarda (2000+ kart) `embed_batch` metodu 500'lük paketler halinde otomatik çalışır.
- Raporlar `anki_jsonlar/` klasörüne dinamik isimlerle kaydedilir.

---
*DUS Mentörü - 2026-05-01*
