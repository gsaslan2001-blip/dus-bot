# MYBRAIN — Furkan'ın Uzun Vadeli Hafıza İndeksi

> **Bu dosya bir LLM bağlam kılavuzudur.** `mybrain` Pinecone indeksini, namespace yapısını ve bellek kullanım protokollerini tanımlar.
> Son güncelleme: 2026-05-09 | v3.3 — **Pinecone-First Mimari**: Arama ve yükleme Pinecone Inference E5 (`get_embedder("pinecone")`). `get_embedder("local")` geriye dönük alias olarak çalışır.

---

## 1. İndeks Kimliği

| Özellik | Değer |
|---------|-------|
| **İndeks Adı** | `mybrain` |
| **Host** | `mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io` |
| **Embedding Modeli** | **Pinecone Inference E5 (multilingual-e5-large, 1024-dim)** |
| **Boyut** | 1024 |
| **Metrik** | Cosine |
| **Tür** | Serverless, AWS us-east-1 |

---

## 2. Namespace Envanteri (Gerçek Yapı)

| Namespace | Kaynak Dizin | İçerik Özeti |
|-----------|--------------|--------------|
| `dus-progress` | `PROGRESS.md`, `WEEKLY/` | Çalışma ilerlemesi ve tamamlanan branşlar. |
| `dus-curriculum` | `CURRICULUM/` | DUS 2026 müfredat akışı ve ünite listeleri. |
| `dus-memory` | `memory/` | Akademik çalışma notları ve derin analizler. |
| `chathistory` | `vektörlenecek/` | Sohbet dökümleri ve oturum bazlı notlar. |
| `telos` | `PAI/USER/TELOS` | Furkan'ın kişisel hedefleri ve TELOS vizyonu. |
| `dus-strategy` | `STRATEGY.md` | DUS çalışma stratejileri ve planlama kararları. |
| `dus-reference` | `REFERENCE/` | Akademik referanslar ve araç setleri. |
| `claude-profile` | `user_profile.md` | Kullanıcı tercihleri ve asistan konfigürasyonu. |

---

## 3. Hibrit Arama ve Kayıt Protokolü

### A. Arama (Ders Çalışma / Sorgulama)
Arama hızı için **Pinecone Integrated Inference** (Managed E5) kullanılır.
- **Yöntem:** `mcp_pinecone-mcp-server_search-records` veya `search_engine.py`.
- **Avantaj:** 500ms altı yanıt süresi, yerel model yükleme beklemesi yok.
- **Reranker:** Tüm aramalarda `bge-reranker-v2-m3` zorunludur.

### B. Yükleme (Vektörleme / Upsert)
**Pinecone Inference E5** (`multilingual-e5-large`) kullanılır — yerel model yok.
- **Yöntem:** `python scripts/dus_uploader.py`.
- **API:** `get_embedder("pinecone")` (`get_embedder("local")` deprecated alias, çalışır).
- **Akış:** Veri önce `vektörlenecek/` (staging) klasörüne yazılır, sonra senkronize edilir.

---

## 4. Senkronizasyon Komutları

```bash
# Chat geçmişini senkronize et:
python scripts/dus_uploader.py --chathistory

# Kişisel hedefleri senkronize et:
python scripts/dus_uploader.py --telos

# Tüm DUS verilerini (Progress, Curriculum, Memory) senkronize et:
python scripts/dus_uploader.py
```

---

## 5. Ebbinghaus Tekrar Entegrasyonu

İlerlemeler `dus-progress` namespace'ine kaydedilirken Ebbinghaus (+1, +3, +7, +15, +30) takvimi otomatik oluşturulur.
- **Örnek:** Patoloji T+7 tekrarı bugün (2026-05-01) başarıyla mühürlendi.

---

*Proje: DUS Mentörü | İndeks: mybrain | v3.3 | 2026-05-09*

