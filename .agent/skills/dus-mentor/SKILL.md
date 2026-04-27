---
name: dus-mentor
description: |
  DUS Mentörü — Furkan'ın DUS 2026 sınavı için Pinecone vektör veritabanı, Supabase soru bankası
  ve Gemini LLM entegrasyonlu akıllı tıp eğitimi asistanı.

  Bu skill şu durumlarda tetiklenir:
  - Kullanıcı bir DUS sorusu, konu başlığı veya kavram ismi gönderdiğinde
  - Pinecone indexleri (mybrain, myppdfs, dusbankasi) üzerinde arama/yazma gerektiğinde
  - Bot scripti (dus_bot.py / main.py) düzenlenecek veya deploy edilecekse
  - Yeni branş PDF'leri Pinecone'a yüklenecekse (upload_*.py akışı)
  - Hafıza kaydı (mybrain/dus-data) veya oturum logu yazılacaksa
  - Cloud Run deployment veya Telegram bot yapılandırması yapılacaksa

  Pinecone index'leri: mybrain (dus-data, claude_memory) | myppdfs (patoloji, endodonti,
  radyoloji, protez, histoloji, fizyoloji, periodontoloji) | dusbankasi (OpenAI embed, 16072 vektör)
  Reranker: bge-reranker-v2-m3 (TÜM aramalarda zorunlu)
  Arama Modları: S2 (kısaca → multi-query) | S5 (kapsamlı → full pipeline)

allowed_tools:
  - mcp_pinecone-mcp-server_search-records
  - mcp_pinecone-mcp-server_upsert-records
  - mcp_pinecone-mcp-server_rerank-documents
  - mcp_pinecone-mcp-server_cascading-search
  - mcp_pinecone-mcp-server_describe-index-stats
  - mcp_pinecone-mcp-server_list-indexes
  - mcp_supabase_execute_sql
  - mcp_supabase_apply_migration
  - mcp_supabase_list_tables
  - mcp_supabase_get_logs
  - run_command
  - view_file
  - write_to_file
  - replace_file_content
  - multi_replace_file_content
  - grep_search
  - list_dir
---

# DUS Mentörü — Skill Orkestrasyon Kılavuzu

## 1. Proje Bağlamı

| Alan | Değer |
|------|-------|
| Proje Klasörü | `C:\Users\FURKAN\Desktop\Projeler\Pinecone` |
| Supabase | `vblndoyjmkgaeuihydyd.supabase.co` (DUSBANK) |
| Cloud Run | `https://dus-mentor-489596239454.europe-west1.run.app` |
| LLM | Gemini — fallback: 2.5-flash → 2.0-flash → 2.0-flash-lite → 3.1-flash-lite-preview → 3.1-pro-preview |

**Dosya Haritası (hızlı referans):**
- `Gemini.MD` → Proje anayasası (mimari kararlar buraya kaydedilir)
- `MYPPDFS.MD` → myppdfs index kılavuzu + S2/S5 arama protokolü
- `MYBRAIN.MD` → mybrain index kılavuzu + hafıza politikası
- `DUSBANKASI.MD` → dusbankasi + Supabase RPC entegrasyon notları
- `scripts/config.py` → merkezi konfigürasyon (API anahtarları os.environ)
- `scripts/dus_bot.py` → Telegram polling botu
- `scripts/main.py` → FastAPI webhook (Cloud Run)
- `scripts/upload_*.py` → branş yükleme scriptleri

---

## 2. Orchestration: Hangi Talep → Hangi Alt Kaynak

```
Kullanıcı girdisi
│
├─ DUS sorusu / konu başlığı
│   └─ workflows/ders_calis.md  →  S5 Full Pipeline
│
├─ "kısaca [konu]"
│   └─ workflows/ders_calis.md  →  S2 Multi-Query Modu
│
├─ "soru üret [konu]"
│   └─ workflows/soru_uret.md
│
├─ "konuştuklarımızı kaydet" / hafıza kaydı
│   └─ workflows/hafiza_kaydet.md
│
├─ Hata / bug / script sorunu
│   └─ workflows/debug.md
│
├─ Pinecone arama/yükleme
│   └─ rules/pinecone_rules.md + ilgili upload_*.py scripti
│
└─ Güvenlik / API anahtarı
    └─ rules/security_rules.md (asla .env okuma)
```

---

## 3. Pinecone Index Operasyonları

### 3.1 Bağlantı Standardı

**Daima host kullan** (`pc.Index(host=HOST)`) — index ismiyle bağlanma, kota limitini zorlar.

```python
# mybrain / myppdfs (Integrated Inference):
index.search(namespace="<ns>", query={"inputs": {"text": "<sorgu>"}, "top_k": 20})

# dusbankasi (Manuel embed — OpenAI text-embedding-3-small):
embedding = openai_client.embeddings.create(input=sorgu, model="text-embedding-3-small").data[0].embedding
index.query(vector=embedding, top_k=10, include_metadata=True)
```

### 3.2 Rerank — Her Aramada Zorunlu

```python
pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query="<orijinal sorgu>",
    documents=[r["fields"]["text"] for r in results.result.hits],
    top_n=5
)
```

### 3.3 Namespace Haritası

| Index | Namespace | Kayıt | Model | İçerik |
|-------|-----------|-------|-------|--------|
| `mybrain` | `dus-curriculum` | ~28 | E5-Large | Müfredat akışı |
| `mybrain` | `dus-memory` | ~135 | E5-Large | Akademik notlar |
| `mybrain` | `dus-progress` | ~16 | E5-Large | İlerleme verileri |
| `mybrain` | `dus-strategy` | ~24 | E5-Large | Strateji dosyaları |
| `mybrain` | `dus-reference` | ~26 | E5-Large | Referans veriler |
| `mybrain` | `telos` | ~46 | E5-Large | Kişisel hedefler |
| `mybrain` | `chathistory` | ~10 | E5-Large | Sohbet logları |
| `mybrain` | `claude_memory` | 297 | E5-Large | AI Sistem belleği |
| `myppdfs` | `patoloji` | 680 | E5-Large | Oral Patoloji |
| `myppdfs` | `...` | ~8k | E5-Large | Diğer Branşlar |
| `dusbankasi` | "" (default) | 16072 | OpenAI ada-3 | 16K+ DUS Sorusu |

### 3.4 Yeni Branş Yükleme Akışı

1. `directives/yeni_brans_ekle.md` direktifini oku
2. `scripts/upload_[brans]_to_pinecone.py` şablonunu `scripts/upload_to_pinecone.py`'dan klonla
3. `chunk_size=1000, overlap=200, batch_size=50` — standart parametreler
4. 429 hatası → exponential backoff: `sleep(2**retry_count * 5)`
5. Yükleme sonrası `MYPPDFS.MD` tablo satırını güncelle
6. `Gemini.MD` görev kuyruğunu ✅ işaretle

---

## 4. Arama Protokolü (S2 / S5)

### S2 — Kısaca Modu (Tetikleyici: "kısaca" kelimesi)

1. Sorguyu 3 perspektife genişlet (klinik / mekanizma / DUS pattern)
2. İlgili namespace'leri paralel tara (`topK=10` / sorgu)
3. `bge-reranker-v2-m3` → `topN=5`
4. Adım 2 formatında kısa yanıt

### S5 — Full Pipeline (Tetikleyici: konu adı / "anlat" / "karşılaştır" / "soru üret")

| Katman | İşlem | Açıklama |
|--------|-------|----------|
| L0 | Local Embedding | Sorguyu yerel CPU'da E5-Large ile vektörle. |
| L1 | Parallel Search | İlgili tüm namespace'leri (mybrain+myppdfs) tara. |
| L2 | Multi-Query | Sorguyu klinik/temel bilim perspektiflerine yay. |
| L3 | Rerank | bge-reranker-v2-m3, topK=15→topN=5 |
| L4 | Sentez | ders_calis.md Adım 0–5 kaskadı (Faz 1) |
| L5 | Çıkmış Entegrasyonu | ders_calis.md Adım 6–8 (Faz 2) — otomatik |

**Faz 2 detayı (her ders çalışma oturumunda Faz 1 ardından zorunlu):**
1. **Adım 6:** Yanıttaki kavramlar çıkarılır → `myppdfs/cikmis` namespace paralel taranır → DUS geçmişi sunulur.
2. **Adım 7:** Bulunan cikmis soruların bilişsel düzeyi, tipi, saptırma stratejisi LLM tarafından analiz edilir.
3. **Adım 8:** Adım 7 kalite profiliyle uyumlu, ancak farklı kavramları sorgulayan 5 yeni DUS sorusu üretilir (2K/2O/1Z).

**Cross-namespace eşleşmeleri:**
- Oral lezyon → `patoloji` + `radyoloji` + `periodontoloji`
- Endodontik konu → `endodonti` + `radyoloji` + `histoloji`
- Protez komplikasyon → `protez` + `patoloji`

---

## 5. Hafıza Kaydetme Protokolü

**"Konuştuklarımızı kaydet"** komutu geldiğinde:

```python
record = {
    "id": "session_full_log-YYYY-MM-DD-HHMM",
    "text": "<tüm sohbet akışı>",
    "source": "antigravity_session",
    "type": "session_full_log",
    "date": "YYYY-MM-DD"
}
# → mybrain / dus-data namespace'ine upsert
```

**Otomatik kayıt tetikleyiciler:** mimari karar | teknik sorun çözümü | yeni branş yükleme | oturum sonu özeti

**Kayıt tipleri:** `session_log` | `session_full_log` | `architecture_decision` | `technical_decision` | `technical_pattern`

---

## 6. Bot Deployment Akışı

### Yerel Polling (dus_bot.py):
```bash
# Webhook çakışmasını kaldır:
python -c "import telebot, os; bot=telebot.TeleBot(os.environ['TELEGRAM_TOKEN']); bot.remove_webhook()"
python scripts/dus_bot.py
```

### Cloud Run Webhook (main.py):
```bash
gcloud builds submit --tag gcr.io/<PROJECT_ID>/dus-mentor
gcloud run deploy dus-mentor --image gcr.io/<PROJECT_ID>/dus-mentor --region europe-west1
```

**Model fallback zinciri** (`config.py`'da tanımlı):
`gemini-2.5-flash-preview` → `gemini-2.0-flash` → `gemini-2.0-flash-lite` → `gemini-3.1-flash-lite-preview` → `gemini-3.1-pro-preview`

---

## 7. Güvenlik Kuralları (Kırmızı Çizgiler)

- `.env` dosyasını ASLA okuma / gösterme / silme
- API anahtarı `os.environ["KEY_NAME"]` — koda gömme
- `delete` (Pinecone) / `DROP` (Supabase) → özel onay al
- Halüsinasyon yapma → "Bilmiyorum, doğrulayalım"
- `run_command` → Furkan onayı olmadan çalıştırma

---

## 8. Definition of Done (Tamamlanma Kontrol Listesi)

### Ders Çalışma Oturumu:
**Faz 1 — İçerik Üretimi:**
- [ ] Adım 0: E5 vektörleme + paralel namespace araması + reranker uygulandı
- [ ] Adım 2: 20/80 High-Yield kimlik kartı üretildi
- [ ] Adım 3: Mekanizma kaskadı + katmanlı mimari var
- [ ] Adım 4: Ayırıcı Tanı Matrisi tablosu var
- [ ] Adım 5: DUS sınav perspektifi yazıldı

**Faz 2 — Çıkmış Entegrasyonu (ZORUNLU, onay beklenmeden):**
- [ ] Adım 6: Kavramlar çıkarıldı → `myppdfs/cikmis` paralel tarandı → DUS geçmişi sunuldu
- [ ] Adım 7: Cikmis soru kalite analizi yapıldı (bilişsel düzey, tip, güçlük profili)
- [ ] Adım 8: 5 yeni DUS sorusu üretildi (cikmis kavramlarından farklı, 2K/2O/1Z)

- [ ] Dil: Türkçe, emoji yok, motivasyon klişesi yok

### Pinecone Yükleme Oturumu:
- [ ] Chunk parametreleri standart (1000/200/50)
- [ ] Retry mekanizması aktif
- [ ] Yükleme sonrası index stats doğrulandı
- [ ] MYPPDFS.MD güncellendi
- [ ] Mimari karar mybrain/dus-data'ya kaydedildi

### Bot Değişikliği:
- [ ] API anahtarı .env üzerinden okunuyor
- [ ] Fallback zinciri config.py'da tanımlı
- [ ] Webhook / polling çakışması kontrol edildi
- [ ] requirements.txt güncel

---

## 9. Hata Yönetimi (Feedback Loop)

| Hata | Aksiyon |
|------|---------|
| 429 Rate Limit (Pinecone) | Exponential backoff, batch küçült |
| 429 RESOURCE_EXHAUSTED (Gemini) | Fallback zinciri — bir sonraki modele geç |
| Webhook Çakışması | `bot.remove_webhook()` → polling moduna al |
| dusbankasi search_records hatası | `query()` + manuel OpenAI embedding akışına geç |
| Boş/belirsiz DUS girdisi | "Geçerli bir DUS sorusu veya konu başlığı gönderilmedi." |
| Kapsam dışı talep | Hangi alana ait olduğunu belirt, DUS bağlantısı varsa işle |

---

## 10. Eksik / Görev Kuyruğu (Aktif)

| Öncelik | Görev | Durum |
|---------|-------|-------|
| 🔴 Yüksek | Tam Yerel (E5) Mimariye Geçiş | ✅ BİTTİ |
| 🔴 Yüksek | mybrain Namespace Reorganizasyonu | ✅ BİTTİ |
| 🟡 Orta | `dusbankasi` için doğrudan Pinecone query() metodu yaz | 🔄 Devam Ediyor |
| 🟢 Düşük | Ebbinghaus tekrar sistemi → mybrain entegrasyonu | 📅 Planlandı |
| 🟢 Düşük | Branş PDF'lerinin E5 ile re-indexi | 🔄 Devam Ediyor |

---

*DUS Mentörü SKILL.md | Proje: `C:\Users\FURKAN\Desktop\Projeler\Pinecone` | Oluşturulma: 2026-04-23*
*Antigravity (Google DeepMind) — DOE Çerçevesi v1.0*
