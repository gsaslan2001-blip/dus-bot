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

### 2. OpenAI Embedding (dusbankasi — zorunlu)
- Çekilen kavramlar `text-embedding-3-small` (1536-dim) ile vektörlenir.
- **Gerekçe:** `dusbankasi` Pinecone indeksi 1536-dim OpenAI mimarisindedir; model değişikliği re-index gerektirir.

### 3. Pinecone (dusbankasi) Semantik Sorgu
- `search_engine.py --questions` ile `dusbankasi` indeksi sorgulanır.
- En alakalı sorular seçilir (Max 20 soru, `--top_n 20`).

**CLI Komutu:**
```bash
python scripts/search_engine.py --questions --lesson "[ders]" --top_n 20 "[kavram sorgusu]"
```
Örnek:
```bash
python scripts/search_engine.py --questions --lesson "patoloji" --top_n 20 "skuamöz hücreli karsinom differansiyasyon"
```

### 4. Çıktı Biçimlendirme (Output)
- **Chatbot Ekranı:** Sadece sorular ve şıklar (A-E) numaralandırılarak kullanıcıya sunulur.
- **Markdown Dosyası:** `RAPORLAR/[KONU]_[GGAAYYYY]_Cevap_Anahtari.md` adıyla cevaplar ve detaylı açıklamalar oluşturulur.
  - Örn: `RAPORLAR/skuamoz_hucreli_karsinom_09052026_Cevap_Anahtari.md`

## 🎯 Hedef
Ezber bozucu, kavramsal ilişkisi yüksek ve sınava en yakın soruları hızlıca filtrelemek.

---
*DUS Mentörü Workflow v1.0*
