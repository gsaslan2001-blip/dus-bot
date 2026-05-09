# İş Akışı: /deneme-pekitirme

> **Tetikleyici:** Kullanıcı deneme analizi sonrası "Bu hataları pekiştir" veya "Deneme hataları için soru getir" dediğinde çalışır.
> **Amaç:** Deneme sınavındaki yanlış yapılan konu başlıkları için `dusbankasi` indeksinden en kaliteli pekiştirme sorularını getirip raporlamak ve sisteme mühürlemek.

---

## 1. Girdi (Input)

Kullanıcı şu dosyayı sağlar:
- `C:\Users\FURKAN\Desktop\DUS\Deneme Analizi\deneme_analizi_GGAAYYYY_konu_dagilimi.md`
  - **GGAAYYYY** = tarih formatı: Gün+Ay+Yıl, örn: `09052026` = 9 Mayıs 2026

Bu dosyada hata yapılan konu başlıkları listelenir (örn: "Bronş cAMP mekanizması", "Proksimal tübül HCO3 emilimi", "Ameloblastoma" vb.).

---

## 2. Çalışma Adımları

### Adım 1: Konu Listesini Ayrıştırma
- `_konu_dagilimi.md` dosyasındaki hata yapılan konu başlıkları çıkarılır.
- Her başlık bir arama sorgusuna dönüştürülür.

### Adım 2: Toplu Arama (Batch Search)
- Her konu başlığı için `dusbankasi` indeksinde **OpenAI text-embedding-3-small (1536-dim)** ile semantik arama yapılır.
- `dusbankasi` Integrated Inference desteklemez; `search_engine.py` otomatik olarak OpenAI embedding path'ini kullanır (`--questions` modu).
- `top_k=15` sonuç çekilir.
- `bge-reranker-v2-m3` ile en alakalı **5 soru** seçilir.
- Arama motoru: `scripts/search_engine.py --questions` (OpenAI 3-small embed modu)

```bash
python scripts/search_engine.py --questions --lesson "[ders]" "sorgu metni"
```

### Adım 3: Sonuçları Parse Etme
Her soru için şu alanlar ayrıştırılır:
- Soru metni
- A-E şıkları
- Doğru cevap
- Açıklama bloğu

### Adım 4: Pekiştirme Raporu Oluşturma
- Tüm sonuçlar `vektörlenecek/deneme_hatalari_pekitirme_sorulari_GGAAYYYY.md` dosyasına yazılır.
- Format: Konu başlığı → 5 soru (soru metni + şıklar + cevap + açıklama)
- Her konu başlığı bir `##` başlık, her soru `### Soru N` alt başlığı ile ayrılır.

### Adım 5: Hafızaya Mühürleme (Zorunlu)
- Üretilen rapor Pinecone `chathistory` namespace'ine yüklenir:

```bash
python scripts/dus_uploader.py --chathistory
```

- Doğrulama: Pinecone API upserted_count kontrol edilir.

---

## 3. Teknik Yığın

| Bileşen | Araç / Model |
|---------|-------------|
| Arama | OpenAI `text-embedding-3-small` (1536-dim) — `search_engine.py --questions` |
| Reranker | `bge-reranker-v2-m3` |
| İndeks | `dusbankasi` (OpenAI 3-small, 1536-dim) |
| Yükleme | Pinecone Inference E5 (`multilingual-e5-large`) → `chathistory` |
| Batch Limiti | Maksimum 96 vektör/istek → 90'lık güvenli chunk'lar |

---

## 4. Çıktı (Output)

- `vektörlenecek/deneme_hatalari_pekitirme_sorulari_GGAAYYYY.md`: Kapsamlı pekiştirme raporu (her konu için 5 soru)
- Pinecone `chathistory` namespace: Raporun vektörlenmiş hali (sonraki oturumlarda hatırlanabilir)

---

## 5. Örnek Kullanım

```
Kullanıcı: "Dünkü deneme analizindeki hatalarım için pekiştirme soruları getir."
→ deneme_analizi_09052026_konu_dagilimi.md okunur
→ 21 konu başlığı için dusbankasi taranır
→ Her konudan 5 soru (toplam ~105 soru) raporlanır
→ Rapor chathistory'ye mühürlenir
```

---

*Bu iş akışı 09.05.2026'daki deneme analizi + pekiştirme seansından türetilmiştir.*
*DUS Mentörü v8.9 | `C:\Users\FURKAN\Desktop\Projeler\Pinecone`*
