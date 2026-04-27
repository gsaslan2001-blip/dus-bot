# 🧪 Workflow: /test-olustur (Gelişmiş Soru Üretim Hattı)

Bu protokol, belirli bir ders ve konu için "anlam odaklı" soru bankası taraması ve test oluşturma sürecini yönetir.

## 📥 Giriş (Input)
- **Ders Adı** (Örn: Patoloji)
- **Konu/Ünite** (Örn: Skuamöz Hücreli Karsinom)

## 🔄 İş Akışı Adımları

### 1. Pinecone Kavram Madenciliği
- `myppdfs` indeksine gidilir.
- İlgili dersin namespace'i ve konusu taranır.
- Konuyla ilişkili en kritik 5-10 kavram (keyword/concept) çekilir.

### 2. OpenAI Embedding
- Çekilen kavramlar `text-embedding-3-small` modeli ile 1536 boyutlu vektörlere dönüştürülür.

### 3. Supabase Semantik Sorgu
- `questions` tablosunda `0.3` benzerlik eşiği (threshold) ile arama yapılır.
- En alakalı sorular seçilir (Max 20 soru).

### 4. Çıktı Biçimlendirme (Output)
- **Chatbot Ekranı:** Sadece sorular ve şıklar (A-E) numaralandırılarak kullanıcıya sunulur.
- **Markdown Dosyası:** `RAPORLAR/[KONU]_Cevap_Anahtari.md` adıyla cevaplar ve detaylı açıklamalar oluşturulur.

## 🎯 Hedef
Ezber bozucu, kavramsal ilişkisi yüksek ve sınava en yakın soruları hızlıca filtrelemek.

---
*DUS Mentörü Workflow v1.0*
