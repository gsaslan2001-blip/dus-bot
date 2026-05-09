# Atlas Telegram Bot — Bayrak Teslim Raporu

**Tarih:** 2026-05-03
**Versiyon:** v9.0
**Durum:** CANLI — Çalışıyor

---

## 1. Proje Özeti

Furkan'ın DUS Mentörü sistemi artık Telegram üzerinden 7/24 erişilebilir. Bot DeepSeek V4 Pro ile çalışır, Pinecone RAG altyapısını kullanır, Railway.app üzerinde barınır.

| Bileşen | Teknoloji | Durum |
|---------|-----------|-------|
| Hosting | Railway.app (us-west2) | Online |
| LLM | DeepSeek V4 Pro (`deeepseek-v4-pro`) | 200 OK |
| Vektör Arama | Pinecone (myppdfs, mybrain, anki) | OpenAI fallback ile çalışıyor |
| Soru Bankası | Supabase | **401 — API key geçersiz** |
| Webhook | https://dus-bot-production.up.railway.app/webhook | Kurulu |

---

## 2. Mimari

```
Telegram Mesajı
     │
     ▼
[FastAPI Webhook] (bot/main.py)
     │
     ├── Komut (/start, /help, /stats, /dersler, /sifirla)
     │   └── Doğrudan yanıt
     │
     └── Normal mesaj
         │
         ▼
     [Router] DeepSeek intent sınıflandırma (5 kategori)
         │
         ▼
     [Orchestrator] Paralel Pinecone araması (asyncio.gather)
         ├── mybrain (hafıza)
         ├── myppdfs (ders notları)
         ├── anki (flashcard)
         └── Supabase (soru bankası)
         │
         ▼
     [Agent Loop] DeepSeek function calling (max 5 iterasyon)
         ├── search_ders_notlari
         ├── search_hafiza
         ├── search_soru_bankasi
         └── search_anki
         │
         ▼
     [DeepSeek Sentez] → Telegram'a chunk'lanmış yanıt (4096 char)
```

---

## 3. Dosya Envanteri

### Yeni Oluşturulanlar (21 dosya)

```
bot/
├── __init__.py              # Path ayarı (scripts/ import için)
├── settings.py              # Pydantic config (.env'den)
├── deps.py                  # Client singleton'ları
├── main.py                  # FastAPI entry point + webhook
├── handlers/
│   ├── commands.py          # /start, /help, /stats, /dersler, /sifirla
│   ├── messages.py          # Ana mesaj handler'ı
│   └── errors.py            # Global hata yakalayıcı
├── services/
│   ├── deepseek_client.py   # AsyncOpenAI → api.deepseek.com
│   ├── router.py            # Intent sınıflandırıcı
│   ├── orchestrator.py      # Çoklu index paralel arama
│   └── agent_loop.py        # Tool-calling agent döngüsü
├── tools/
│   └── search_tools.py      # 4 tool + execute dispatcher
└── prompts/
    └── system_prompt.py     # Atlas persona + DUS kuralları
```

### Deployment Dosyaları
```
Dockerfile              # Python 3.12-slim, sadece requirements-bot.txt
.dockerignore           # .env, tmp/, archive/ hariç
requirements-bot.txt    # Minimal bağımlılıklar (torch YOK)
.env.example            # Değişken şablonu
```

### Değiştirilen Mevcut Dosyalar
```
scripts/search_engine.py    # Local E5 yoksa OpenAI 1024-dim fallback eklendi
smart_dedup_addon/config.json  # API key'ler placeholder ile değiştirildi
```

---

## 4. Environment Variables (Railway)

Tüm değişkenler Railway dashboard'da tanımlı:
https://railway.com/project/e3f5db40-b7eb-49c0-a4f9-ac55d101314a

| Variable | Durum |
|----------|-------|
| `TELEGRAM_TOKEN` | Güncel |
| `DEEPSEEK_API_KEY` | Güncel (`sk-f9e9...`) |
| `PINECONE_API_KEY` | Güncel |
| `OPENAI_API_KEY` | Güncel (fallback embedding) |
| `SUPABASE_URL` | Güncel |
| `SUPABASE_KEY` | **GEÇERSİZ — yenilenmeli** |
| `MYBRAIN_HOST` | Güncel |
| `MYPPDFS_HOST` | Güncel |
| `ANKI_HOST` | Güncel |
| `BASE_URL` | Güncel (Railway domain) |
| `ALLOWED_CHAT_IDS` | `806847622` (Furkan) |

---

## 5. Bilinen Sorunlar ve Aksiyonlar

### Kritik
| # | Sorun | Aksiyon | Kim |
|---|-------|---------|-----|
| 1 | **Supabase API key geçersiz** (401) | Supabase dashboard → Project Settings → yeni anon key al → Railway'de `SUPABASE_KEY` güncelle | Furkan |
| 2 | **mybrain Integrated Inference yok** | Pinecone console → mybrain index → Integrated Inference → `multilingual-e5-large` seç | Furkan |
| 3 | **anki Integrated Inference yok** | Pinecone console → anki index → Integrated Inference → `multilingual-e5-large` seç | Furkan |

### Orta
| # | Sorun | Etki | Not |
|---|-------|------|-----|
| 4 | Router JSON parse hatası | Intent "genel"e düşüyor, myppdfs atlanıyor | Agent loop tool calling ile telafi ediyor |
| 5 | myppdfs 0 sonuç dönüyor | "ders_calis" intent'i atlanınca ilk aşamada aranmıyor | Agent `search_ders_notlari` ile manuel arıyor |
| 6 | OpenAI fallback embedding maliyeti | Her aramada ~$0.0001 | Integrated Inference etkinleşince SIFIR |

### Düzeltildi
| # | Sorun | Commit |
|---|-------|--------|
| 7 | `finish_reason` AttributeError | `c248660` |
| 8 | DeepSeek 401 (eski key) | Railway'de güncellendi |
| 9 | Docker torch/sentence-transformers (2GB+) | `ac15d3b` |

---

## 6. Maliyet

| Servis | Aylık Tahmin |
|--------|-------------|
| Railway.app | $0 (free tier) |
| DeepSeek V4 Pro | ~$3-8 (1000 mesaj) |
| Pinecone | $0 (serverless free) |
| OpenAI embedding (fallback) | ~$0.50-2 |
| Supabase | $0 (free tier) |
| **TOPLAM** | **~$5-10/ay** |

**Not:** mybrain ve anki'de Integrated Inference etkinleşince OpenAI embedding maliyeti SIFIRLANIR.

---

## 7. Komutlar

| Komut | İşlev |
|-------|-------|
| `/start` | Hoş geldin mesajı |
| `/help` | `/start` ile aynı |
| `/stats` | Pinecone + Supabase istatistikleri |
| `/dersler` | DUS branş listesi |
| `/sifirla` | Sohbet bağlamını temizle |

---

## 8. Deploy Akışı

GitHub'a push → Railway otomatik deploy (Dockerfile):

```bash
git add -A && git commit -m "..." && git push
```

Railway CLI manuel deploy:
```bash
railway up
```

Log izleme:
```bash
railway logs --lines 50
```

---

## 9. Doğrulanan Çalışma

Son test (`Radyoloji Artefakt konusunu detaylıca açıkla`):

```
1. Router: intent=genel (JSON parse hatası nedeniyle)
2. Orchestrator: brain=5, anki=3 (pdfs intent "genel" olduğu için atlandı)
3. Agent Loop: 5 iterasyon
   - İterasyon 1: search_ders_notlari + search_soru_bankasi + search_anki
   - İterasyon 2: search_ders_notlari (kon-kat, banyo artefaktları)
   - İterasyon 3: search_ders_notlari (KIBT artefakt)
   - İterasyon 4: search_ders_notlari (banyo artefaktları)
   - İterasyon 5: DeepSeek sentez (4096 token çıktı)
4. Yanıt: 2 chunk halinde gönderildi (4000+ karakter)
```

---

## 10. Öneriler

1. **Supabase key'ini yenile** — soru bankası şu an çalışmıyor
2. **mybrain + anki Integrated Inference'ı etkinleştir** — OpenAI maliyetini sıfırlar, hızı artırır
3. **Router'ı iyileştir** — DeepSeek bazen JSON yerine ham string dönüyor, keyword-based fallback eklenebilir
4. **myppdfs için "genel" intent'te de arama ekle** — router hatası olsa bile ders notları aransın

---

**Bayrak Furkan'da. Atlas 7/24 nöbette.**
