# 🚀 Pinecone-First Embedding Mimarisi (DUS Mentörü)

Bu belge, DUS Mentörü projesinde embedding stratejisini kesin olarak belirler.
**Yerel model (sentence-transformers) tamamen kaldırılmıştır.** Tüm embedding işlemleri Pinecone Inference API veya OpenAI üzerinden yapılır.

## 1. Kesin Kullanım Sınırları

| Alan | İşlem | Yöntem / Model | Gerekçe |
|------|-------|----------------|---------|
| **Ders Çalışma (PDF/Notlar)** | Arama (Query) | **Pinecone Integrated Inference (E5)** | Hız ve 500ms altı yanıt süresi. |
| **Hafıza / Kayıt (Upload)** | Vektörleme (Upsert) | **Pinecone Inference API (E5 1024-dim)** | Yerel model gerektirmez, sunucu tarafında embedding. |
| **Arama Fallback** | Vektörleme | **Pinecone Inference API (E5 1024-dim)** | Integrated Inference başarısız olursa Pinecone embed + query. |
| **Anki Ekosistemi** | **Vektörleme & Dedup** | **OpenAI Large (3072-dim)** | Eklenti (smart_dedup_addon) ile tam uyum ve yüksek hassasiyet. |
| **Soru Bankası (Supabase)** | Arama (Query) | **OpenAI (3-small, 1536-dim)** | `text-embedding-3-small` ile embedding üretilir. |
| **Anki (Dedup & Upload)** | Vektörleme & Arama | **OpenAI (3-large, 3072-dim)** | `text-embedding-3-large`, eklenti ve `anki_uploader.py` uyumu için zorunlu. |

## 2. Neden OpenAI Anki'de Zorunlu?

1. **Mirror Mode:** Yerel Anki eklentisi (`smart_dedup_addon`) OpenAI Large (3072) kullanır. Pinecone'daki `anki` indeksiyle birebir kıyaslama yapabilmek için aynı model zorunludur.
2. **Hassasiyet:** Tıbbi terminolojideki ince farkları (Tip 1 vs Tip 2) yakalamak için yüksek boyutlu (3072) vektörler gereklidir.

## 3. Akıllı Tekilleştirme (Smart Dedup) Standartları

Anki kartları işlenirken şu protokol uygulanır:

1. **Vektörleme:** Kart içeriği OpenAI `text-embedding-3-large` ile 3072 boyuta çevrilir.
2. **Kıyaslama (Pinecone):** `anki` indeksindeki mevcut kartlarla benzerlik sorgusu yapılır.
3. **Eşik (Threshold):** **0.84** ve üzeri benzerlik "aday kopya" olarak işaretlenir.
4. **Lexical Guard:** Eğer benzerlik yüksekse ancak "Tip, Evre, Sınıf, Grade, Stage, Faz" gibi kritik sayısal belirteçler farklıysa, kart **mükerrer sayılmaz**.

## 4. Geliştirici Kılavuzu

### Arama (Ders Çalış)
```bash
python scripts/search_engine.py --index myppdfs --ns radyoloji "Sorgu metni"
```
*(Arka planda Integrated Inference veya Pinecone Inference API fallback tetiklenir.)*

### Embedding Üretme
```python
from embedding_utils import get_embedder

# Pinecone Inference API (myppdfs/mybrain, 1024-dim)
vec = get_embedder("pinecone").embed_text("içerik", is_query=False)

# OpenAI (anki/dusbankasi)
vec = get_embedder("openai", dimension=3072).embed_text("içerik")
```

---
*DUS Mentörü Pinecone-First Mimari Belgesi - 2026-05-03 | v5.0 — Yerel Embedding KALDIRILDI*
