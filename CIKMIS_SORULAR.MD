# 🗂️ CIKMIS_SORULAR — DUS Çıkmış Soru Dataset Kılavuzu

> **Bu dosya** `dus_jsonlari/` klasöründeki 2015–2026 DUS çıkmış soru datasetini tanımlar.
> Son güncelleme: 2026-04-26 | v1.1

---

## 1. Dataset Özeti

| Alan | Değer |
|------|-------|
| **Kapsam** | 2015 – 2026 (12 sınav yılı) |
| **Toplam JSON** | 14 dosya (bazı yıllar 2 dönem) |
| **Tam Soru** | ~1641 (şıklı) |
| **Format** | `{yil}-{donem}-dus.json` |
| **Konum** | `dus_jsonlari/` |
| **Kaynak PDF** | `C:\Users\FURKAN\Desktop\DUS\Çıkmış\dus çıkmış\dus eski\` |
| **Pinecone Index**| `myppdfs` |
| **Namespace** | `cikmis` |
| **Vektör Sayısı** | 1560 |

---

## 2. JSON Şema (Standart)

Her soru kaydı **tam olarak** bu alanları içerir:

```json
{
  "id":         "dus_2025-2_q007",
  "soru_no":    7,
  "yil":        "2025-2",
  "donem":      "Sonbahar 2025",
  "bolum":      "Temel Bilimler",
  "ders":       "Histoloji ve Embriyoloji",
  "kaynak_pdf": "DUS 2025 2.Dönem Soruları.pdf",
  "iptal":      false,
  "soru_metni": "Soru gövdesi...",
  "secenekler": { "A": "...", "B": "...", "C": "...", "D": "...", "E": "..." },
  "raw_text":   "Soru gövdesi... A) ... B) ... E) ..."
}
```

> `raw_text` = Pinecone semantic search için birleşik metin. Her zaman dolu olmalı.

---

## 3. Dosya Envanteri

| Dosya | Yıl | Dönem | Kaynak |
|-------|-----|-------|--------|
| `2015-dus.json` | 2015 | Tek Dönem | PDF |
| `2016-dus.json` | 2016 | Tek Dönem | PDF |
| `2017-dus.json` | 2017 | Tek Dönem | PDF |
| `2018-1-dus.json` | 2018 | Bahar | PDF |
| `2018-2-dus.json` | 2018 | Sonbahar | PDF |
| `2019-1-dus.json` | 2019 | Bahar | PDF |
| `2019-2-dus.json` | 2019 | Sonbahar | PDF |
| `2020-dus.json` | 2020 | Tek Dönem | PDF |
| `2021-dus.json` | 2021 | Tek Dönem | PDF |
| `2022-dus.json` | 2022 | Tek Dönem | PDF |
| `2023-2-dus.json` | 2023 | Sonbahar | PDF |
| `2025-1-dus.json` | 2025 | Bahar | PDF + MD Patch |
| `2025-2-dus.json` | 2025 | Sonbahar | PDF + MD Patch |
| `2026-1-dus.json` | 2026 | Bahar | PDF |

---

## 4. Yeni Sınav Ekleme

**Çıkmış Ekle** workflow'u: `.agent/workflows/cikmis_ekle.md`

```bash
# Yeni PDF parse
python scripts/cikmis_ekle.py --pdf "DUS 2026 1. Dönem.pdf" --yil 2026 --donem 1

# Denetim
python scripts/cikmis_ekle.py --audit 2026-1-dus.json

# MD patch (opsiyonel)
python scripts/cikmis_ekle.py --patch-md "DUS 2026 1.md" --json 2026-1-dus.json
```

---

## 5. Ders Dağılımı (Her Sınav)

| Q | Bölüm | Ders |
|---|-------|------|
| 1–6 | Temel | Anatomi |
| 7–10 | Temel | Histoloji ve Embriyoloji |
| 11–16 | Temel | Fizyoloji |
| 17–22 | Temel | Tıbbi Biyokimya |
| 23–28 | Temel | Tıbbi Mikrobiyoloji |
| 29–32 | Temel | Tıbbi Patoloji |
| 33–36 | Temel | Tıbbi Farmakoloji |
| 37–40 | Temel | Tıbbi Biyoloji ve Genetik |
| 41–50 | Klinik | Restoratif Diş Tedavisi |
| 51–60 | Klinik | Protetik Diş Tedavisi |
| 61–70 | Klinik | Ağız, Diş ve Çene Cerrahisi |
| 71–80 | Klinik | Ağız, Diş ve Çene Radyolojisi |
| 81–90 | Klinik | Periodontoloji |
| 91–100 | Klinik | Ortodonti |
| 101–110 | Klinik | Endodonti |
| 111–120 | Klinik | Pedodonti |

---

## 6. Kalite Kriterleri

| Durum | Kriter | Aksiyon |
|-------|--------|---------|
| ✅ Başarılı | ≥ 110/120 tam şıklı | Pinecone'a yüklenebilir |
| ⚠️ Kabul edilebilir | 95–110 tam şıklı | Görsel sorular eksik olabilir |
| ❌ Hata | < 95 tam şıklı | `cikmis_ekle.py` ile debug et |

---

## 7. Arama ve Erişim

Sorulara `myppdfs` indeksi üzerinden `cikmis` namespace'i ile erişilebilir. Her kayıt zengin metadata içerir:
- `text`: Soru + Şıklar (Embedding alanı)
- `yil`, `donem`, `bolum`, `ders`, `soru_no`
- `doc_type`: "cikmis_soru"

---
*DUS Mentörü v7.2 | 2026-04-26*
