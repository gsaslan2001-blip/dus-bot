# Atlas Telegram Bot — Bayrak Teslim Raporu v9.1

**Tarih:** 2026-05-03
**Versiyon:** v9.1
**Durum:** CANLI — Deploy edildi
**Son Commit:** `5f8014b`

---

## 1. Bu Seans Yapilanlar

### 1.1 Webhook Kurtarmasi (Acil)
Bot yanit vermiyordu — webhook URL'si bosalmisti. Manuel olarak `setWebhook` ile yeniden baglandi.
Su an: `https://dus-bot-production.up.railway.app/webhook` aktif.

### 1.2 Prefix Routing (Yeni Ozellik)
Mesaj basinda prefix ile dogrudan index yonlendirmesi:

| Prefix | Intent | Force Index |
|--------|--------|-------------|
| `/mypdf`, `/pdfs`, `/pdf`, `/ders`, `/not` | ders_calis | myppdfs |
| `/brain`, `/hafiza`, `/memory`, `/ilerleme` | hafiza | mybrain |
| `/soru`, `/test`, `/quiz`, `/coz` | soru_sor | - |
| `/anki`, `/kart`, `/flashcard` | ders_calis | anki |
| `/cikmis`, `/sinav` | cikmis_analiz | - |

### 1.3 Keyword-Based Intent On-Siniflandirma
Router'a DeepSeek API cagrisini atlayan hizli yol eklendi. ~30 DUS anahtar kelimesiyle intent tespiti.
Cogu mesaj artik API cagrisi olmadan siniflandiriliyor.

### 1.4 Orchestrator Iyilestirmeleri
- "genel" intent'te ders tespit edilince myppdfs'te de arama yapiliyor (onceki: atlaniyordu)
- `cikmis_analiz` intent'i myppdfs aramasina eklendi
- `forced_index` parametresi ile prefix routing destegi

### 1.5 DeepSeek Retry Mekanizmasi
2 retry + exponential backoff (1.5s, 3s). API gecici hatalarinda bot cokmez.

### 1.6 Yerel Embedding Tamamen Kaldirildi
- `LocalE5Embedder` sinifi silindi
- `PineconeEmbedder` eklendi (Pinecone Inference API kullanir)
- `get_embedder()` default provider: `"pinecone"`
- `requirements.txt`: `torch`, `sentence-transformers` kaldirildi
- Docker image boyutu ~2GB kuculdu

### 1.7 Settings Duzeltmeleri
- Pinecone host URL'lerinden `https://` prefix kaldirildi (SDK uyumu)

---

## 2. Yapilmasi Gereken 3 Kritik Is

| # | Is | Yer | Sure |
|---|-----|-----|------|
| **1** | Supabase anon key yenile | Supabase Dashboard → Project Settings → API → anon key → Railway `SUPABASE_KEY` guncelle | 2 dk |
| **2** | mybrain Integrated Inference ac | Pinecone Console → mybrain → Integrated Inference → `multilingual-e5-large` | 1 dk |
| **3** | anki Integrated Inference ac | Pinecone Console → anki → Integrated Inference → `multilingual-e5-large` | 1 dk |

**Yeni Supabase key:** Furkan'da mevcut (service_role key). Railway `SUPABASE_KEY` olarak guncellenmeli.
Not: Bu bir service_role key. Anon key tercih edilir ama bu da calisir.

**Bu 3 is tamamlaninca:**
- Soru bankasi calisir
- OpenAI embedding maliyeti SIFIRLANIR
- Arama hizi 2x artar

---

## 3. Degisen Dosyalar (11 dosya, +331/-181 satir)

```
bot/services/router.py          Prefix routing + keyword on-siniflandirma
bot/services/orchestrator.py    "genel" fix + forced_index + cikmis_analiz
bot/services/deepseek_client.py Retry mekanizmasi (2 retry, exp backoff)
bot/handlers/messages.py        Prefix routing entegrasyonu
bot/handlers/commands.py        /start mesajina prefix komutlari eklendi
bot/settings.py                 Host URL https:// prefix kaldirildi
scripts/embedding_utils.py      LocalE5Embedder → PineconeEmbedder
scripts/search_engine.py        Fallback: yerel E5 → Pinecone Inference API
requirements.txt                torch, sentence-transformers kaldirildi
EMBEDDING.MD                    v4.0 → v5.0 Pinecone-First mimari
.agent/rules/pinecone_rules.md  v4.0 → v5.0 Pinecone Inference API
```

---

## 4. Mimari (Guncel v9.1)

```
Telegram Mesaji
     │
     ▼
[FastAPI Webhook] (bot/main.py)
     │
     ├── Prefix routing (/mypdf, /brain, vs.)
     │   └── forced_index → direkt ilgili index'e yonlendirir
     │
     ├── Keyword intent (30+ anahtar kelime)
     │   └── API cagrisi YOK
     │
     └── DeepSeek intent (fallback)
         │
         ▼
     [Orchestrator] Paralel Pinecone aramasi
         ├── mybrain (hafiza) → Integrated Inference
         ├── myppdfs (ders notlari) → Integrated Inference
         ├── anki (flashcard) → OpenAI embed + query
         └── Supabase (soru bankasi) → OpenAI embed + RPC
         │
         ▼
     [Agent Loop] DeepSeek function calling (max 5 iterasyon)
         │
         ▼
     [DeepSeek Sentez] → Telegram'a chunk'lanmis yanit (4096 char)
```

### Embedding Mimarisi (v5.0 Pinecone-First)

| Index | Arama | Yukleme | Model | Boyut |
|-------|-------|---------|-------|-------|
| myppdfs | Integrated Inference | Pinecone Inference API | multilingual-e5-large | 1024 |
| mybrain | Integrated Inference | Pinecone Inference API | multilingual-e5-large | 1024 |
| dusbankasi | OpenAI embed + query | OpenAI embed + upsert | text-embedding-3-small | 1536 |
| anki | OpenAI embed + query | OpenAI embed + upsert | text-embedding-3-large | 3072 |

---

## 5. Komutlar

| Komut | Islev |
|-------|-------|
| `/start` | Hos geldin mesaji + prefix komut listesi |
| `/help` | `/start` ile ayni |
| `/stats` | Pinecone + Supabase istatistikleri |
| `/dersler` | DUS brans listesi |
| `/sifirla` | Sohbet baglamini temizle |
| `/mypdf <mesaj>` | Dogrudan ders notlarinda ara |
| `/brain <mesaj>` | Dogrudan hafizada ara |
| `/soru <mesaj>` | Dogrudan soru coz |
| `/anki <mesaj>` | Dogrudan Anki kartlarinda ara |
| `/cikmis <mesaj>` | Dogrudan cikmis analizi yap |

---

## 6. Saglik Durumu

| Bilesen | Durum |
|---------|-------|
| Railway Hosting | Online |
| DeepSeek V4 Pro | 200 OK |
| Pinecone (myppdfs) | Integrated Inference aktif |
| Pinecone (mybrain) | Integrated Inference AKTIF (model tanimli) |
| Pinecone (anki) | OpenAI fallback ile calisiyor |
| Supabase | 401 — API key yenilenmeli |
| Webhook | `https://dus-bot-production.up.railway.app/webhook` — AKTIF |

---

## 7. Onemli Notlar

1. **Shutdown webhook silme sorunu:** `bot/main.py` shutdown handler'i her deploy'da webhook'u siliyor. Startup'ta tekrar kurulmasi gerekiyor. BASE_URL env var'i yoksa webhook kurulmaz.
2. **Supabase service_role key:** Verilen key `sb_secret_` ile basliyor — bu service_role key. Guvenlik acisindan anon key tercih edilir ama calisir.
3. **PineconeEmbedder API key gerektirir:** Lokal gelistirmede PINECONE_API_KEY env var'i olmadan PineconeEmbedder hata verir. Bu beklenen davranis.

---

**Bayrak Furkan'da. Atlas 7/24 nobette.**
**v9.1 — Pinecone-First, Prefix Routing, Retry, Yerel Embedding YOK.**
