# Workflow: Soru Üret (`/soru-uret`)

**Açıklama:** Belirli bir konu veya branş için DUS formatında çoktan seçmeli soru üret.

---

## Adımlar

### 1. Parametreleri Al
- Hangi branş? (Patoloji / Endodonti / Radyoloji / Protez / Histoloji / Fizyoloji / Periodontoloji)
- Hangi konu? (Ör: "nekroz mekanizmaları", "kök kanal irrigasyon protokolü")
- Kaç soru? (Varsayılan: 5)
- Zorluk seviyesi? (Temel / Orta / Zor — Varsayılan: Orta)

### 2. Pinecone'dan Kaynak Çek
- İlgili namespace'de konuyu ara (topK=20, rerank topN=5)
- Birden fazla kaynaktan bilgi topla (hibrit arama)

### 3. Soru Üret

Her soru şu formatta olmalı:

```
**Soru [N]:** [Klinik senaryo veya doğrudan soru]

A) [Seçenek]
B) [Seçenek]
C) [Seçenek]
D) [Seçenek]
E) [Seçenek]

> **Cevap:** [Harf] — [Kısa gerekçe]
```

### 4. Kalite Kontrol
Her soru üretmeden önce kontrol et:
- [ ] Klinik senaryo gerçekçi mi?
- [ ] Doğru cevap tartışmasız mı?
- [ ] Yanlış seçenekler mantıklı tuzaklar içeriyor mu?
- [ ] DUS soru formatına uyuyor mu?

### 5. Kaydet (Opsiyonel)
Furkan "kaydet" derse:
1. Soruları `vektörlenecek/soru_uret_[konu]_[GGAAYYYY].md` olarak kaydet.
2. `python scripts/dus_uploader.py --chathistory` ile `mybrain/chathistory` namespace'ine yükle.
   - ID formatı (metadata): `"question_batch-[konu]-YYYY-MM-DD"`, type: `"generated_questions"`

---

## Tamamlanma Kriteri
İstenen sayıda soru üretildi, her birinde cevap + gerekçe var = TAMAMLANDI
