# 🗄️ DUSBANKASI — DUS Soru Bankası Vektör İndeksi

> **Bu dosya bir LLM bağlam kılavuzudur.** `dusbankasi` Pinecone indeksini ve Supabase entegrasyonunu tanımlar.
> Son güncelleme: 2026-04-23

---

## 1. İndeks Kimliği

| Özellik | Değer |
|---------|-------|
| **İndeks Adı** | `dusbankasi` |
| **Host** | `dusbankasi-0crkhvy.svc.aped-4627-b74a.pinecone.io` |
| **Embedding Modeli** | OpenAI `text-embedding-3-small` (**Manuel, integrated değil**) |
| **Boyut** | 1536 |
| **Metrik** | Cosine |
| **Tür** | Serverless, AWS us-east-1 |
| **Toplam Kayıt** | **16.312** (16.072 Eski + 240 Yeni 2025) |
| **Standardize Dataset** | 2015-2025 JSON (120 Soru/Sınav) |
| **Namespace** | `""` (boş/default) |

---

## 2. ⚠️ Kritik Uyarılar

### 2.1 API Uyumsuzluğu (ÖNEMLİ)

Bu index, `search_records` MCP aracıyla doğrudan **çalışmaz.** Sebebi:
- `dusbankasi` **integrated inference** kullanmıyor → MCP'nin `search_records` metodu embedding oluşturamaz
- API 2025-04+ sonrası boş string namespace (`""`) kabul etmiyor → `__default__` veya doğrudan `query()` kullanılmalı

**Doğru kullanım:**
```python
# Adım 1: Sorguyu önce OpenAI ile embed et
import openai
response = openai.embeddings.create(input=sorgu, model="text-embedding-3-small")
embedding = response.data[0].embedding  # 1536 boyutlu vektör

# Adım 2: Pinecone'a embedding ile sorgula (SDK query metodu)
index = pc.Index(host="dusbankasi-0crkhvy.svc.aped-4627-b74a.pinecone.io")
results = index.query(vector=embedding, top_k=5, include_metadata=True)
```

### 2.2 Bot'taki Gerçek Kullanım

`dus_bot.py`'de `search_questions()` fonksiyonu bu index'i **doğrudan sorgulamıyor.** Bunun yerine **Supabase `match_questions_semantic` RPC**'sini kullanıyor. `dusbankasi` index'i gelecekte paralel veya yedek katman olarak değerlendirilecek.

---

## 3. Supabase Entegrasyonu

| Özellik | Değer |
|---------|-------|
| **Proje** | `vblndoyjmkgaeuihydyd.supabase.co` (DUSBANK) |
| **Tablo** | `questions` |
| **RPC Fonksiyonu** | `match_questions_semantic` |
| **Embedding Alanı** | `embedding` (pgvector, 1536 boyut) |

**Çalışma Akışı:**
```
Kullanıcı sorusu
    → OpenAI text-embedding-3-small
    → Supabase match_questions_semantic RPC
    → En benzer DUS soruları döner
    → Gemini soruyu/cevabı biçimlendirir
```

---

## 4. İçerik

| Alan | Değer |
|------|-------|
| **Toplam Soru** | 16.312 |
| **Kapsam** | DUS soru bankası + 2015-2025 Çıkmış (Standardize) |
| **Veri Kaynağı** | `dus_jsonlari/` (Standardize JSON Dataset) |

---

## 5. Gelecek Planı

| Görev | Durum |
|-------|-------|
| Supabase RPC üzerinden arama | ✅ Aktif (`search_questions`) |
| Yeni Sınav Ekleme Motoru (`cikmis_ekle.py`) | ✅ Aktif |
| 2025 PDF-to-JSON Standardizasyonu | ✅ Tamamlandı |
| `dusbankasi` MCP uyumlu hale getirilmesi | ❌ Bekliyor |

---

*Bu dosya Antigravity (Google DeepMind) tarafından oluşturuldu.*
*Proje: DUS Mentörü | İndeks: dusbankasi | Klasör: `C:\Users\FURKAN\Desktop\Projeler\Pinecone\DUSBANKASI.MD`*
