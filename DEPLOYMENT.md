# 🚀 DUS Mentörü — Cloud Run Deployment Kılavuzu (7/24)

## Mimari

```
Telegram → Cloud Run (webhook) → Gemini 2.5 Flash
                    ↓
          Pinecone (mybrain + myppdfs)
          Supabase (DUSBANKASI sorular)
          OpenAI (embedding)
```

**Bilgisayarın kapalı olabilir.** Cloud Run mesaj gelince uyanır, yanıtlar, uyur. Maliyet ≈ 0₺.

---

## ADIM 1 — Google Cloud Hazırlık

1. https://console.cloud.google.com → Giriş yap
2. Yeni proje oluştur: `dus-mentor-bot`
3. Cloud Run API'yi etkinleştir:
   ```
   https://console.cloud.google.com/apis/library/run.googleapis.com
   ```
4. Artifact Registry API'yi etkinleştir:
   ```
   https://console.cloud.google.com/apis/library/artifactregistry.googleapis.com
   ```

---

## ADIM 2 — Google Cloud CLI Kur (Windows)

```powershell
# https://cloud.google.com/sdk/docs/install adresinden indirip kur
# Kurulumdan sonra:
gcloud auth login
gcloud config set project dus-mentor-bot
```

---

## ADIM 3 — Deploy Et

```powershell
# Proje klasörüne gir
cd "C:\Users\FURKAN\Desktop\Projeler\Pinecone"

# Docker imajını build et ve push et
gcloud builds submit --tag gcr.io/dus-mentor-bot/dus-mentor

# Cloud Run'a deploy et (ENV değişkenlerini .env'den al)
gcloud run deploy dus-mentor `
  --image gcr.io/dus-mentor-bot/dus-mentor `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated `
  --set-env-vars "TELEGRAM_TOKEN=SENIN_TOKEN,GEMINI_API_KEY=SENIN_KEY,PINECONE_API_KEY=SENIN_KEY,OPENAI_API_KEY=SENIN_KEY,SUPABASE_URL=SENIN_URL,SUPABASE_KEY=SENIN_KEY"
```

> ⚠️ `europe-west1` seç — Türkiye'ye en yakın bölge.

Deploy sonrası URL şöyle görünür:
```
https://dus-mentor-xxxx-ew.a.run.app
```

---

## ADIM 4 — Telegram Webhook'u Ayarla

Tarayıcıya yapıştır (TOKEN ve URL'yi değiştir):

```
https://api.telegram.org/botSENIN_TOKEN/setWebhook?url=https://dus-mentor-xxxx-ew.a.run.app/webhook
```

Başarılı yanıt:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

Webhook durumunu kontrol etmek için:
```
https://api.telegram.org/botSENIN_TOKEN/getWebhookInfo
```

---

## ADIM 5 — Test Et

Telegram'da bota yaz: `/start`

Bot cevap verirse 🎉 — artık bilgisayarsız, 7/24 çalışıyor!

---

## Güncellemeler

Kodu değiştirince yeniden deploy et:

```powershell
gcloud builds submit --tag gcr.io/dus-mentor-bot/dus-mentor
gcloud run deploy dus-mentor --image gcr.io/dus-mentor-bot/dus-mentor --region europe-west1
```

---

## Maliyet

| Servis | Ücretsiz Kota | Beklenen Maliyet |
|--------|--------------|-----------------|
| Cloud Run | 2M istek/ay | **0₺** |
| Pinecone | 1GB | **0₺** |
| Gemini API | Ücretsiz kota | **0₺** |
| Supabase | 500MB | **0₺** |

---

## Komutlar

| Komut | Açıklama |
|-------|----------|
| `/start` | Karşılama mesajı |
| `/help` | Yardım |
| `/stats` | Pinecone + Supabase istatistikleri |
| Normal mesaj | Agent loop → Gemini + Tools |
