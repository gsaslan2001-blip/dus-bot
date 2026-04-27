# DUS Mentörü Botu v2.0 🦷

Bot başarıyla güncellendi ve yeni yetenekler eklendi!

## 🚀 Yeni Özellikler
1. **DUSBANKASI Entegrasyonu (Supabase):** Artık 10.000+ soruluk bankandan benzer soruları ve açıklamalarını getirebiliyorum.
   - *Örn:* "Hücre hasarı ile ilgili 2 soru getir"
   - *Örn:* "Endodonti'den kanal tedavisi soruları göster"
2. **Gelişmiş Ajan Döngüsü:** Tek bir mesajda birden fazla araç kullanabilirim (Hem notlarına bakıp hem soru getirebilirim).
3. **Sistem Durumu (/stats):** `/stats` komutu ile Pinecone ve Supabase bağlantılarını kontrol edebilirsin.
4. **Hata Yönetimi:** Gemini modelleri arasında otomatik geçiş (Flash -> Lite -> 1.5) ile kesintisiz hizmet.

## 🛠️ Kullanılan Araçlar
- **search_memory:** Senin çalışma ilerleyişin ve özel notların.
- **search_pathology:** Patoloji ders notlarındaki klinik detaylar.
- **search_questions:** Supabase'deki soru bankası (OpenAI embedding destekli).
- **remember_fact:** Önemli bilgileri hafızana kaydeder.

## 📦 Kurulum
Gerekli kütüphaneler yüklendi (`openai`, `supabase`, `google-genai`).
Botu başlatmak için:
```bash
python dus_bot.py
```

*Not: Pinecone ve Supabase API anahtarları dosya içerisinde güvenli bir şekilde yapılandırılmıştır.*
