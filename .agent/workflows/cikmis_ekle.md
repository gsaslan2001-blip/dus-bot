# 📥 Çıkmış Soru Ekleme Protokolü (DUS Mentörü)

> **⚠️ TALİMAT:** Yeni bir DUS sınav PDF'i verildiğinde bu protokol EKSİKSİZ uygulanmalıdır.
> Format, 2015–2025 dataset standardına göre belirlenmiştir.
> İlgili script: `scripts/cikmis_ekle.py`

---

## Giriş: Standart JSON Formatı

Her soru kaydı şu metadata alanlarını içermelidir:

```json
{
  "id":         "dus_{yil}_q{soru_no:03d}",
  "soru_no":    1,
  "yil":        "2025-2",
  "donem":      "Sonbahar 2025",
  "bolum":      "Temel Bilimler",
  "ders":       "Anatomi",
  "kaynak_pdf": "DUS 2025 2.Dönem Soruları.pdf",
  "iptal":      false,
  "soru_metni": "Soru gövdesi...",
  "secenekler": {
    "A": "Şık A metni",
    "B": "Şık B metni",
    "C": "Şık C metni",
    "D": "Şık D metni",
    "E": "Şık E metni"
  },
  "raw_text": "Soru gövdesi... A) Şık A metni B) Şık B metni ... E) Şık E metni"
}
```

### Ders/Bölüm Eşleme Tablosu (Sabit)

| Soru Aralığı | Bölüm | Ders |
|---|---|---|
| 1–6 | Temel Bilimler | Anatomi |
| 7–10 | Temel Bilimler | Histoloji ve Embriyoloji |
| 11–16 | Temel Bilimler | Fizyoloji |
| 17–22 | Temel Bilimler | Tıbbi Biyokimya |
| 23–28 | Temel Bilimler | Tıbbi Mikrobiyoloji |
| 29–32 | Temel Bilimler | Tıbbi Patoloji |
| 33–36 | Temel Bilimler | Tıbbi Farmakoloji |
| 37–40 | Temel Bilimler | Tıbbi Biyoloji ve Genetik |
| 41–50 | Klinik Bilimler | Restoratif Diş Tedavisi |
| 51–60 | Klinik Bilimler | Protetik Diş Tedavisi |
| 61–70 | Klinik Bilimler | Ağız, Diş ve Çene Cerrahisi |
| 71–80 | Klinik Bilimler | Ağız, Diş ve Çene Radyolojisi |
| 81–90 | Klinik Bilimler | Periodontoloji |
| 91–100 | Klinik Bilimler | Ortodonti |
| 101–110 | Klinik Bilimler | Endodonti |
| 111–120 | Klinik Bilimler | Pedodonti |

---

## Adım 1: PDF Alımı ve Doğrulama

- PDF dosyasını `C:\Users\FURKAN\Desktop\DUS\Çıkmış\dus çıkmış\dus eski\` altına yerleştir.
- Dosya adı formatı: `DUS {YYYY} {N}. Dönem Orijinal Sorular.pdf`
- Yıl ve dönem bilgisini belirle: **1. Dönem → Bahar**, **2. Dönem → Sonbahar**
- PDF sayfa sayısını ve cevap anahtarı sayfası varlığını kontrol et.

## Adım 2: PDF Parse

`scripts/cikmis_ekle.py` scriptini çalıştır:

```bash
python scripts/cikmis_ekle.py \
  --pdf "DUS 2025 3. Dönem Orijinal Sorular.pdf" \
  --yil 2025 \
  --donem 3 \
  --out dus_jsonlari/2025-3-dus.json
```

Script aşağıdakileri otomatik yapar:
1. **Çift sütun koordinat bazlı okuma** (sol/sağ sütun bağımsız parse)
2. **Cevap anahtarı sayfası tespiti** ve atlanması (`CEVAP ANAHTARI` regex)
3. **Şık çekimi**: `A) … B) … C) … D) … E) …` satır içi veya blok format
4. **Metadata enjeksiyonu**: `ders`, `bolum`, `id`, `raw_text` otomatik atanır
5. **Kalite raporu**: Kaç soru tam/eksik parse edildiği özetlenir

## Adım 3: Kalite Denetimi

Parse sonrası çıktıyı değerlendir:
- **≥ 110/120 tam şıklı** → Başarılı, Pinecone'a yüklenebilir
- **95–110** → Görsel/tablo sorular eksik olabilir; kabul edilebilir
- **< 95** → Hata var, PDF yapısı farklı olabilir; debug et

Eksik şıklı soruları belirle:
```bash
python scripts/cikmis_ekle.py --audit 2025-3-dus.json
```

## Adım 4: MD Patch (Opsiyonel)

PDF parse eksikse, eğer kaynak MD dosyası varsa hibrid patch uygula:
```bash
python scripts/cikmis_ekle.py \
  --patch-md "DUS 2025 3. Dönem Soruları.md" \
  --json dus_jsonlari/2025-3-dus.json
```

## Adım 5: Pinecone'a Yükleme

JSON hazır olduktan sonra `myppdfs` veya `dusbankasi` indeksine yükle:
```bash
python scripts/cikmis_ekle.py \
  --upload dus_jsonlari/2025-3-dus.json \
  --index dusbankasi \
  --namespace cikmis-2025
```

---

## Dosya Konumları

| İşlev | Konum |
|---|---|
| Kaynak PDF'ler | `C:\Users\FURKAN\Desktop\DUS\Çıkmış\dus çıkmış\dus eski\` |
| Üretilen JSON'lar | `C:\Users\FURKAN\Desktop\Projeler\Pinecone\dus_jsonlari\` |
| Parse scripti | `C:\Users\FURKAN\Desktop\Projeler\Pinecone\scripts\cikmis_ekle.py` |
| Build scriptleri (geliştirme) | `C:\Users\FURKAN\.gemini\antigravity\scratch\` |

---

## Notlar

- **İptal edilen sorular** `"iptal": true, "raw_text": "İptal edilmiş soru"` olarak işaretlenir.
- **Görsel/tablo soruları** şıksız kalabilir — bu beklenen bir davranıştır, `"iptal": false` olarak kalır.
- **`raw_text`** alanı Pinecone semantic search için kritiktir — her zaman dolu olmalıdır.
- Mevcut JSON formatını kesinlikle değiştirme; tüm sürümler aynı şemaya uymalıdır.

---
*Bu protokol `build_2025_from_pdf.py` + `patch_2025_from_md.py` deneyiminden türetilmiştir.*
*Güncelleme: 2026-04-26 | DUS Mentörü v7.1*
