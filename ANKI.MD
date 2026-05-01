# ANKI.MD — Anki Kart Kalite Güvencesi ve `anki` İndeks Kılavuzu

> Son güncelleme: 2026-04-29 | v1.0
> Bu kılavuz, `anki` Pinecone indeksinin yapısını, iş akışını, script API'lerini ve AnkiConnect entegrasyonunu belgeler.

---

## 1. Amaç

Anki kartlarının **benzersizliğini** sağlamak ve yeni eklenen kartların mevcut koleksiyonla anlamsal olarak örtüşüp örtüşmediğini tespit etmek. Çift veya çok benzer bilgileri sınayan kartları elimine ederek kart sayısını düşürmek ve çalışma verimini artırmak.

**Kapsam:** DUS branşlarına ait Cloze-MAXXİNG ve Basic-AnKing formatındaki kartlar.

---

## 2. Pinecone `anki` İndeksi

| Alan              | Değer                                                   |
|-------------------|---------------------------------------------------------|
| **Index Adı**     | `anki`                                                  |
| **Host**          | `anki-0crkhvy.svc.aped-4627-b74a.pinecone.io`           |
| **Boyut**         | 1024 (Multilingual-E5-Large)                            |
| **Metrik**        | Cosine                                                  |
| **Cloud/Region**  | AWS / us-east-1                                         |
| **Embedding**     | **YEREL** — `multilingual-e5-large` (Bulut YASAK)       |

### Namespace Yapısı

Her ders/branş için ayrı namespace:

| Namespace   | İçerik                              |
|-------------|-------------------------------------|
| `protez`    | Protetik diş hekimliği kartları     |
| `radyoloji` | Radyoloji branşı kartları           |
| `[branş]`   | Gelişen tüm DUS branşları           |

---

## 3. Kart Veri Şeması (JSON Standardı)

### 3.1 Cloze-MAXXİNG Kartı

```json
{
  "id": "z!Zx)KuOg6",
  "guid": "z!Zx)KuOg6",
  "ders": "protez",
  "unite": "dis_morfolojisi",
  "deck_full": "DUS::Protetik::00-Dis Morfolojisi",
  "kart_tipi": "cloze",
  "text_raw": "Okluezal tabla: {{c1::Tuberkuller}} ve ...",
  "text_clean": "Okluezal tabla: Tuberkuller ve marjinal sirtlar arasinda...",
  "baslik": "dis anatomisi",
  "extra": "",
  "vektorlenecek_metin": "dis anatomisi | Okluezal tabla: Tuberkuller ve..."
}
```

### 3.2 Basic-AnKing Kartı

```json
{
  "id": "B-OVGzEaX1",
  "guid": "B-OVGzEaX1",
  "ders": "radyoloji",
  "unite": "radyoloji_fizigi",
  "deck_full": "DUS::Radyoloji::001-Radyoloji Fizigi",
  "kart_tipi": "basic",
  "front": "Tipta tani ve tedavi alaninda radyan enerji kullanimini inceleyen bilim dali nedir?",
  "back": "Radyoloji -.",
  "baslik": "Radyoloji - Temel Kavramlar - Tanim",
  "extra": "",
  "text_clean": "Tipta tani ve tedavi... Radyoloji -.",
  "vektorlenecek_metin": "Radyoloji - Temel Kavramlar | Tipta tani ve tedavi..."
}
```

### 3.3 Vektörlenecek Metin Formülü

```
vektorlenecek_metin = baslik + " | " + text_clean
```

- **Cloze:** `text_clean` = Cloze isaretleri (`{{c1::X}}`) temizlenmis duz metin
- **Basic:** `text_clean` = `front + " " + back`
- Baslik bossa: yalnizca `text_clean` kullanilir

---

## 4. Embedding Kurallari

- **Model:** `multilingual-e5-large` (Yerel, HuggingFace cache)
- **Model Yolu:** `C:\Users\FURKAN\.cache\huggingface\hub\models--intfloat--multilingual-e5-large\snapshots\3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3`
- **Interface:** `get_local_embedder()` — `scripts/embedding_utils.py`
- **Passage modu:** `embed_batch(texts, is_query=False)` — yukleme icin
- **Query modu:** `embed_text(text, is_query=True)` — dedup sorgulari icin
- **Boyut:** 1024

BULUT EMBEDDING KESINLIKLE YASAK.

---

## 5. Pipeline ve Is Akisi

Projede iki farkli deduplication akisi kullanilabilir:

### A. Ekleme Oncesi Dedup ve Otomatik Ekleme (Onerilen - Pre-Import)
Bu akis, desteye cop kart dolmasini en basindan engeller.

```
Yeni Kartlar (Kiyaslanacak TXT)
     |
anki_parser.py  ->  anki_jsonlar/{ders}_kiyas_{unite}.json
     |
anki_dedup.py    -> anki_jsonlar/{ns}_dedup_report.json / .txt (Pinecone ile kiyas)
     |
[KULLANICI: Raporu incele, json'dan kopya olanlari sil]
     |
anki_add_unique.py -> AnkiConnect ile kalan essiz (unique) kartlari Anki'ye ekle
     |
anki_uploader.py -> Yeni eklenen kartlari Pinecone'a yukle (Veritabanini guncelle)
```

**Adim Adim Kullanim:**
```bash
# 1. Parse: Yeni kartlari kiyaslamak uzere JSON'a cevir
python scripts/anki_parser.py "C:\anki\kiyaslanacak.txt" --ders protez --unite kiyas_dis_morfolojisi

# 2. Dedup: Yeni kartlari Pinecone veritabaniyla karsilastir
python scripts/anki_dedup.py --ns protez

# 3. Anki'ye Ekle: Rapor sonucunda ayiklanan benzersiz kartlari Anki'ye ekle
python scripts/anki_add_unique.py

# 4. Pinecone'u Guncelle: Yeni kartlari indeks veritabanina kat
python scripts/anki_uploader.py --json anki_jsonlar/protez_kiyas_dis_morfolojisi.json --ns protez
```

### B. Ekleme Sonrasi Temizlik (Geleneksel - Post-Import)
Zaten Anki'de bulunan kartlarin kendi arasinda temizlenmesi.

```
Anki TXT Export
     |
anki_parser.py  ->  anki_jsonlar/{ders}_{unite}.json
     |
anki_uploader.py -> Pinecone `anki` (GUID manifest)
     |
anki_dedup.py    -> anki_jsonlar/{ns}_dedup_report.json / .txt
     |
[KULLANICI: Raporu incele, to_delete.txt olustur]
     |
anki_delete.py   -> AnkiConnect (Anki'den sil) + Pinecone silme
```

---

## 6. Script API Referansi

### anki_parser.py

Anki TXT export dosyasini okur, standart JSON uretir.
Hem Cloze-MAXXiNG hem Basic-AnKing desteklenir.
Karisik dosyalarda her iki format otomatik ayristiriir.

Cikti: anki_jsonlar/{ders}_{unite}.json

Argumanlar:
- `input`    TXT dosyasi yolu
- `--ders`   Brans adi (kucuk harf, ornek: protez)
- `--unite`  Unite adi (kucuk harf, _ ile, ornek: dis_morfolojisi)

### anki_uploader.py

JSON -> Pinecone `anki` yukleyici.
GUID tabanli manifest (anki_manifest.json) ile degismeyenleri atlar.
Yerel E5 ile batch embedding yapar.

Argumanlar:
- `--json`      Yuklenecek JSON dosyasi
- `--ns`        Hedef namespace (ornek: protez)
- `--all`       anki_jsonlar/ altindaki tum JSON'lari yukle
- `--force`     Manifest gormeزden gel, hepsini yeniden yukle
- `--dry-run`   Yukleme yapma, sadece say

### anki_dedup.py

Namespace'deki tum kartlar icin Pinecone'a embedding sorgusu atar.
Benzerlik >= threshold olan ciftleri JSON + TXT rapor olarak kaydeder.
Capraz format (Cloze <-> Basic) karsilastirmasi desteklenir.

Argumanlar:
- `--ns`          Analiz edilecek namespace
- `--threshold`   Benzerlik esigi (varsayilan: 0.90)
- `--top-k`       Her kart icin sorgulanacak komsu sayisi (varsayilan: 10)

Ciktilar:
- `anki_jsonlar/{ns}_dedup_report.json`  ham veri
- `anki_jsonlar/{ns}_dedup_report.txt`   okunabilir rapor

### anki_add_unique.py

Pinecone dedup raporundan sonra JSON dosyasında kalan eşsiz kartları, AnkiConnect aracılığıyla otomatik olarak Anki'ye ekler.
`Cloze-MAXXİNG` ve `Basic-AnKing` not tiplerini destekler.

Argümanlar:
- `--json`     Eşsiz kartların bulunduğu JSON dosyası (örn: `anki_jsonlar/protez_kiyas_dis_morfolojisi.json`)
- `--deck`     Anki'de eklenecek hedef deste (JSON içindeki `deck_full` değerini ezerse diye, varsayılan JSON içindekini kullanır)

### anki_delete.py

GUID listesini (to_delete.txt) alir:
1. AnkiConnect (localhost:8765) uzerinden Anki'den notu siler
2. Pinecone `anki` namespace'inden vektoru kaldirir
3. anki_manifest.json'u temizler

Argumanlar:
- `--file`           GUID listesi dosyasi (her satir bir GUID)
- `--guids`          GUID'leri dogrudan gir
- `--ns`             Pinecone namespace
- `--dry-run`        Hicbir seyi silme, sadece raporla
- `--pinecone-only`  Sadece Pinecone'dan sil
- `--anki-only`      Sadece Anki'den sil

---

## 7. AnkiConnect Entegrasyonu

### Gereksinimler

- Anki acik olmali
- AnkiConnect eklentisi yuklu olmali (ID: 2055492159)
- URL: `http://localhost:8765`

### GUID -> noteId Mekanizmasi

Anki TXT export'unda her kartin benzersiz GUID'i bulunur.
`anki_delete.py`, bu GUID'i AnkiConnect'in `findNotes` + `notesInfo`
API'siyle Anki'nin internal `noteId`'sine cevirir ve `deleteNotes` ile siler.

### Onemli Not

Anki kapali iken `anki_delete.py` calistirilirsa:
- `--pinecone-only` parametresiyle yalnizca Pinecone temizlenir
- Anki temizligi icin Anki'yi acip tekrar calistirin

---

## 8. Benzerlik Raporu Okuma Kilavuzu

`*_dedup_report.txt` dosyasindaki her cift:

```
[1] SCORE: 0.9742
  KART A (cloze) | GUID: z!Zx)KuOg6
  Baslik: dis anatomisi
  Metin : Okluezal tabla: Tuberkuller ve marjinal sirtlar...

  KART B (basic) | GUID: B-OVGzEaX1
  Baslik: Radyoloji - Temel Kavramlar
  Metin : Tipta tani ve tedavi...
```

Karar rehberi:

| Score       | Oneri                                                        |
|-------------|--------------------------------------------------------------|
| >= 0.95     | Neredeyse kesin duplikat, ikisinden birini sil               |
| 0.90 - 0.95 | Cok benzer, icerigi karsilastir, zayif olani sil             |
| 0.85 - 0.90 | Benzer konu farkli perspektif, genellikle tutulabilir        |
| < 0.85      | Farkli kartlar, muhtemelen ikisi de gerekli                  |

---

## 9. Manifest (anki_manifest.json)

`scripts/anki_manifest.json` yuklenenmis kartlarin GUID hash'lerini tutar.

Ornek:
```json
{
  "protez::z!Zx)KuOg6": {
    "hash": "a3f1c2d...",
    "namespace": "protez",
    "ders": "protez",
    "unite": "dis_morfolojisi"
  }
}
```

Degismeyen kartlar yeniden embed edilmez, kota tasarrufu saglar.

---

## 10. Dosya Dizini

```
C:\Users\FURKAN\Desktop\Projeler\
├── Pinecone\
│   ├── anki_jsonlar\
│   │   ├── protez_dis_morfolojisi.json
│   │   ├── radyoloji_radyoloji_fizigi.json
│   │   ├── protez_dedup_report.json
│   │   ├── protez_dedup_report.txt
│   │   └── to_delete.txt
│   └── scripts\
│       ├── anki_parser.py
│       ├── anki_uploader.py
│       ├── anki_dedup.py
│       ├── anki_delete.py
│       ├── anki_manifest.json
│       └── embedding_utils.py
└── anki\
    ├── 1-Morfoloji.txt
    └── Radyoloji-Radyoloji Fizigi.txt
```

---

## 11. Hizli Referans

```bash
# Yeni ders ekle
python scripts/anki_parser.py "C:\...\yeni_ders.txt" --ders endodonti --unite pulpa_biyolojisi
python scripts/anki_uploader.py --json anki_jsonlar/endodonti_pulpa_biyolojisi.json --ns endodonti

# Tum namespace'leri tara (dedup)
python scripts/anki_dedup.py --ns protez
python scripts/anki_dedup.py --ns radyoloji

# Anki olmadan sadece Pinecone temizligi
python scripts/anki_delete.py --file anki_jsonlar/to_delete.txt --ns protez --pinecone-only

# Sadece Anki temizligi
python scripts/anki_delete.py --file anki_jsonlar/to_delete.txt --ns protez --anki-only

# Degisen kartlari yeniden yukle
python scripts/anki_uploader.py --json anki_jsonlar/protez_dis_morfolojisi.json --ns protez --force

# Tum namespace'leri yukle
python scripts/anki_uploader.py --all
```

---

*ANKI.MD v1.0 | DUS Mentoru | 2026-04-29*
