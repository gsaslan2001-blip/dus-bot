# Atlas Telegram Bot — Bayrak Teslim Raporu v9.2

**Tarih:** 2026-05-03
**Versiyon:** v9.2
**Durum:** CANLI — Deploy edildi, çalışıyor
**Son Commit:** `e4b6d90`

---

## 1. Bu Seans Yapılanlar

### 1.1 Supabase API Key Yenilendi (Kritik)
Eski anon key 401 hatası veriyordu. Furkan'dan alınan yeni service_role key ile değiştirildi:
- `.env`: `SUPABASE_KEY` güncellendi
- **Railway:** `railway variables --set SUPABASE_KEY=sb_secret_k-eQdOs...`
- Sonuç: Supabase sorguları artık `HTTP/2 200 OK` dönüyor.

### 1.2 Ayarlar Menüsü (`/ayarlar`) — YENİ
Telegram inline keyboard ile canlı ayar değiştirme:
- **3 Hız Modu:** Hızlı / Dengeli / Kapsamlı
- **2 Model:** DeepSeek V4 Pro / DeepSeek Reasoner
- **Arama Derinliği:** 2-10 arası ±1 butonlarla
- **Reranking Toggle:** Aç/Kapat
- **Sıfırla:** Varsayılan ayarlara dön

Dosyalar: `bot/handlers/commands.py` (cmd_settings + handle_settings_callback), `bot/main.py` (callback_query handler, user_settings cache)

### 1.3 Hız Optimizasyonları
- **Arama cache (5 dk TTL):** Aynı sorgu tekrar gelirse Pinecone'a gitmeden cevaplar
- **Hızlı Mod:** Agent loop 1 iterasyon, tek namespace araması, brain/anki atlanır
- **Dengeli Mod:** 3 iterasyon (önceki: 5), cross-namespace arama
- **Kapsamlı Mod:** 5 iterasyon, tüm kaynaklar taranır
- Agent loop model override desteği (settings'ten seçilen model kullanılır)

Dosyalar: `bot/services/orchestrator.py`, `bot/services/agent_loop.py`, `bot/services/deepseek_client.py`, `bot/handlers/messages.py`

### 1.4 Prompt İyileştirmeleri
- **TABLO YASAK:** Telegram markdown tabloları desteklemediği için tablo formatı tamamen yasaklandı. Karşılaştırmalar liste formatında yapılacak.
- **Yeni Yanıt Formatı:**
  1. HIGH YIELD (ilk paragraf: en kritik noktalar)
  2. TÜM KONU (mekanizma düzeyinde kapsamlı anlatım)
  3. DUS TUZAKLARI (sık karıştırılanlar)
  4. 5 DUS SORUSU (tüm şıkların mekanistik açıklamasıyla)
- **SYSTEM_PROMPT_FAST:** Hızlı mod için kısaltılmış prompt (846 chars vs 2400 chars)

Dosya: `bot/prompts/system_prompt.py`

### 1.5 Reranking Konfigürasyonu
- `RERANKER_MODEL` artık env var'dan okunabilir (varsayılan: `bge-reranker-v2-m3`)
- `BACKUP_RERANKER_MODEL` tanımlandı
- Ayarlar menüsünden reranking toggle edilebilir

Dosya: `scripts/search_engine.py`

---

## 2. Değişen Dosyalar (9 dosya)

```
bot/settings.py                 Kullanıcı ayarları yapısı, hız modu konfigleri
bot/main.py                     v9.0→v9.2, callback query, /ayarlar, cache
bot/handlers/commands.py        cmd_settings() + handle_settings_callback()
bot/handlers/messages.py        User settings + cache entegrasyonu
bot/services/orchestrator.py    Hız moduna göre akıllı arama yönlendirme
bot/services/agent_loop.py      Model override, SYSTEM_PROMPT_FAST
bot/services/deepseek_client.py Model parametresi eklendi
bot/prompts/system_prompt.py    TABLO YASAK, yeni format, SYSTEM_PROMPT_FAST
scripts/search_engine.py        Reranker env var konfigürasyonu
```

---

## 3. Mimari (Güncel v9.2)

```
Telegram Mesajı
     │
     ▼
[FastAPI Webhook] (bot/main.py)
     │
     ├── Callback Query? → handle_settings_callback() → Inline Keyboard
     │
     ├── Komut? → /start /help /stats /dersler /sifirla /ayarlar
     │
     └── Normal Mesaj → handle_message()
         │
         ├── Prefix routing (/mypdf, /brain, vs.)
         ├── Keyword intent (30+ anahtar kelime) → API YOK
         └── DeepSeek intent (fallback, sadece belirsiz mesajlar)
         │
         ▼
     [Orchestrator] Paralel Pinecone araması (cache kontrollü)
         ├── mybrain (hafıza) → Integrated Inference + Rerank
         ├── myppdfs (ders notları) → Integrated Inference + Rerank
         ├── anki (flashcard) → Integrated Inference / OpenAI fallback
         └── Supabase (soru bankası) → OpenAI embed + RPC ✅ ÇALIŞIYOR
         │
         ▼
     [Agent Loop] DeepSeek function calling
         ├── Hızlı: 1 iterasyon
         ├── Dengeli: 3 iterasyon
         └── Kapsamlı: 5 iterasyon
         │
         ▼
     [DeepSeek Sentez] → Telegram (4096 char chunk'lanmış)
```

---

## 4. Embedding Mimarisi (v5.0 Pinecone-First — Değişmedi)

| Index | Arama | Yükleme | Model | Boyut |
|-------|-------|---------|-------|-------|
| myppdfs | Integrated Inference | Pinecone Inference API | multilingual-e5-large | 1024 |
| mybrain | Integrated Inference | Pinecone Inference API | multilingual-e5-large | 1024 |
| dusbankasi | OpenAI embed + query | OpenAI embed + upsert | text-embedding-3-small | 1536 |
| anki | Integrated Inference / OpenAI fallback | OpenAI embed + upsert | text-embedding-3-large | 3072 |

---

## 5. Komutlar

| Komut | İşlev |
|-------|-------|
| `/start` | Hoş geldin mesajı + komut listesi |
| `/ayarlar` | **YENİ** — Inline keyboard ile bot ayarları |
| `/stats` | Pinecone + Supabase istatistikleri |
| `/dersler` | DUS branş listesi |
| `/sifirla` | Sohbet bağlamını temizle |
| `/mypdf <mesaj>` | Doğrudan ders notlarında ara |
| `/brain <mesaj>` | Doğrudan hafızada ara |
| `/soru <mesaj>` | Doğrudan soru çöz |
| `/anki <mesaj>` | Doğrudan Anki kartlarında ara |
| `/cikmis <mesaj>` | Doğrudan çıkmış analizi yap |

---

## 6. Sağlık Durumu

| Bileşen | Durum |
|---------|-------|
| Railway Hosting | ✅ Online |
| DeepSeek V4 Pro | ✅ 200 OK |
| Pinecone (myppdfs) | ✅ Integrated Inference aktif |
| Pinecone (mybrain) | ✅ Integrated Inference aktif |
| Pinecone (anki) | ✅ Calışıyor |
| Supabase | ✅ 200 OK (yeni key ile) |
| Webhook | ✅ `dus-bot-production.up.railway.app/webhook` |

---

## 7. Bilinen Sorunlar

1. **Router DeepSeek fallback parse hatası:** `'"intent"'` KeyError. Mesaj "Tip 1 tip 2..." gibi kısa/teknik query'lerde DeepSeek intent JSON'ı bozuk dönebiliyor. `genel`'e düşüp devam ediyor, kritik değil.
2. **Railway host URL'lerinde `https://` prefix:** v9.1'de kaldırıldı denmiş ama Railway env var'larında hala var. Pinecone SDK tolere ediyor, sorun çıkmadı.
3. **Shutdown webhook silme:** `main.py` shutdown handler'ı her deploy'da webhook'u siliyor. Startup'ta tekrar kuruluyor, sorun değil.
4. **Supabase service_role key:** `sb_secret_` prefix'li. Güvenlik açısından anon key tercih edilir ama şu an çalışıyor.

---

## 8. Yapılması Gerekenler (Sonraki Seans)

| # | İş | Öncelik |
|---|-----|---------|
| 1 | Pinecone Console → mybrain Integrated Inference → `multilingual-e5-large` model ata | Yüksek |
| 2 | Pinecone Console → anki Integrated Inference → `multilingual-e5-large` model ata | Yüksek |
| 3 | Supabase anon key'e geri dön (güvenlik) | Orta |
| 4 | Router parse hatasını düzelt (KeyError: "intent") | Düşük |
| 5 | Reply markup ile daha zengin mesaj formatları | Düşük |

**mybrain + anki Integrated Inference açılınca:** OpenAI embedding maliyeti sıfırlanır, arama hızı 2x artar.

---

## 9. Faydalı Komutlar

```bash
# Railway'de yeniden deploy
railway up --detach

# Logları izle
railway logs

# Env var güncelle
railway variables --set "KEY=VALUE"

# Deploy durumu
railway status
```

---

**Bayrak Furkan'da. Atlas 7/24 nöbette.**
**v9.2 — Ayarlar Menüsü, Hız Optimizasyonu, TABLO YASAK, Supabase Fix.**
