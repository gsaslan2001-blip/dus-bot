# 📖 Ders Çalışma Protokolü (DUS Mentörü)
> Son güncelleme: 2026-04-27 | v2.0 — Çıkmış Entegrasyon Katmanı eklendi.

> **⚠️ TALİMAT:** Bir konu anlatımı veya soru çözümü talebi geldiğinde bu protokol EKSİKSİZ uygulanmalıdır. Tüm aramalar **PARALEL** (multi-namespace) olarak yürütülmelidir.

---

## ── FAZI 1: İÇERİK ÜRETME (S5 Pipeline) ──────────────────────

### Adım 0: Konu Vektörleme & Pinecone Araması
*Her konu/soru için otomatik tetiklenir.*
- Konuyu yerel E5-Large ile vektörle → `embedder.embed_text("query: " + konu, is_query=True)`
- İlgili namespace'leri **paralel** tara (branşa göre cross-namespace haritası: Adım 0b).
- `top_k=15` ile aday çek → `bge-reranker-v2-m3` ile `top_n=5`'e düşür.
- Reranked sonuçlar Adım 2–4'ün kaynak materyalini oluşturur.

**Cross-namespace haritası (Adım 0b):**
| Konu Tipi | Taranacak Namespace'ler |
|-----------|------------------------|
| Oral lezyon / tümör | `patoloji` + `radyoloji` + `histoloji` |
| Endodontik | `endodonti` + `radyoloji` + `histoloji` |
| Periodontal | `periodontoloji` + `patoloji` + `radyoloji` |
| Protez / Oklüzyon | `protez` + `patoloji` |
| Cerrahi | `cerrahi` + `radyoloji` + `patoloji` |
| Pedodonti | `pedodonti` + `patoloji` + `radyoloji` |
| Farmakoloji | `farmakoloji` |
| Fizyoloji | `fizyoloji` |

---

### Adım 1: Soru Dekompozisyonu
*Sadece bir DUS sorusu geldiyse uygulanır.*
- Branş, konu alanı ve alt başlık tespiti.
- Bilişsel düzey (Hatırlama / Analiz / Uygulama) tespiti.
- Doğru cevabın mekanistik gerekçesi.
- Yanlış şıkların eliminasyon mantığı.

---

### Adım 2: 20/80 High-Yield Özüt Katmanı
*Konunun "kimlik kartı".*
- **Taksonomik Konum:** Konunun hiyerarşideki yeri.
- **Patognomonik Özellikler:** SADECE bu konuya has özellikler.
- **Pattern Recognition:** "Soru çözdüren" anahtar kelime eşleşmeleri.
- **Kritik Fark:** En yakın benzerinden ayıran tek nokta.

---

### Adım 3: Kapsamlı Konu Notu
- **Bilgi Gruplama:** Kategorik alt başlıklar.
- **Eş Hiyerarşi Kıyaslaması:** Bilgiyi izole vermeme, benzerlerle kıyaslama.
- **Mekanizma Zorunluluğu:** A → B → C kaskad formatında neden-sonuç zinciri.
- **Katmanlı Mimari:** Yapı → Klinik → Tanı → Tedavi → Ayırıcı Tanı.

---

### Adım 4: Ayırıcı Tanı Matrisi
*Tablo formatında sunulur.*
| Kavram | Ortak Özellik | Ayırt Edici Fark | DUS Tuzak Açısı |
|--------|--------------|-----------------|-----------------|

---

### Adım 5: DUS Sınav Perspektifi
- Çıkan soru tipleri ve tuzak şık stratejileri.
- Sık karıştırılan kavram çiftleri analizi.

---

## ── FAZI 2: ÇIKMIŞ ENTEGRASYON KATMANI ───────────────────────

> Bu faz, her ders çalışma oturumunda Faz 1'in hemen ardından **otomatik olarak** çalıştırılır.
> Pinecone MCP aracı kullanılır. Adım 6 ve 7 mümkünse paralel tetiklenir.

---

### Adım 6: Kavram Çıkarımı & Çıkmış Taraması
*Faz 1 yanıtı üretildikten sonra otomatik başlar.*

**6a — Kavram Çıkarımı:**
Faz 1'de üretilen yanıtın tamamından anahtar tıbbi kavramları çıkar:
- Hastalık isimleri, sendromlar, lezyonlar
- Histopatolojik terimler, radyolojik bulgular
- Tedavi yöntemleri, ilaç grupları, prosedürler
- Ayırıcı tanıda geçen tüm kavramlar

**6b — Paralel Çıkmış Araması:**
Her kavram için `myppdfs/cikmis` namespace'ini tara:
```
index: myppdfs  |  namespace: cikmis  |  top_k: 5/kavram
reranker: bge-reranker-v2-m3  |  top_n: 3/kavram
```
- Tüm kavramlar için **paralel** arama yap (sıralı değil).
- Eşleşen soruları yıla göre grupla.

**6c — Çıkmış Sunumu:**
Bulunan soruları şu formatta sun:

```
📋 DUS'TA BU KONUDAN ÇIKANLAR
─────────────────────────────────
[Kavram: X]
  • [Yıl] — [Soru metni özeti] (Branş: Y)
  • [Yıl] — [Soru metni özeti] (Branş: Y)

[Kavram: Z]
  • ...
```

*Hiç soru bulunamazsa:* `"Bu konuda myppdfs/cikmis namespace'inde eşleşme bulunamadı."` yaz.

---

### Adım 7: Çıkmış Kalite Analizi
*Bulunan cikmis soruları LLM tarafından analiz edilir.*

Aşağıdaki boyutları değerlendir:

| Boyut | Açıklama |
|-------|----------|
| **Bilişsel Düzey** | Hatırlama / Kavrama / Uygulama / Analiz |
| **Soru Tipi** | Senaryo tabanlı / Tanımlayıcı / Hesaplama / Fotoğraf yorumlama |
| **Saptırma Stratejisi** | Benzer mekanizma tuzağı / Terminoloji tuzağı / İstisnayı sorgulama |
| **Konsept Derinliği** | Temel bilgi / Klinik korelasyon / Mekanizma zinciri |
| **Ortalama Güçlük** | Kolay / Orta / Zor |

**Çıktı formatı:**
```
📊 ÇIKMIŞ SORU ANALİZİ
─────────────────────────────────
Dominant Bilişsel Düzey : [...]
Baskın Soru Tipi       : [...]
Saptırma Stratejisi    : [...]
Konsept Derinliği      : [...]
Güçlük Profili         : [...]

Özet: "[DUS bu konuyu genellikle X açısından, Y seviyesinde sorgular. Z tuzağı sıkça kullanılır.]"
```

---

### Adım 8: 5 DUS Tipi Yeni Soru Üretimi
*Adım 7 analizinin kalite/sorgulama standardını kullan, ancak FARKLI kavramları sorgula.*

**Üretim Kuralları:**
1. Adım 7'de belirlenen **bilişsel düzey, soru tipi ve güçlük profili** korunur.
2. Adım 7'de bulunan cikmis sorularında **geçen kavramlar kullanılmaz** — yanyana komşu kavramlar, mekanizma zincirinin bir üst/alt halkası, ya da ayırıcı tanı alternatifleri hedeflenir.
3. Her soru gerçekçi klinik senaryo içerir.
4. Çeldiriciler mantıklı ve DUS sınav standardına uygun olur.
5. Dağılım: **2 Kolay / 2 Orta / 1 Zor**.

**Çıktı formatı (her soru için):**

```
❓ SORU [N] — [Güçlük]
─────────────────────────────────
[Klinik senaryo veya tanımlama]

A) ...
B) ...
C) ...
D) ...
E) ...

✅ Cevap: [Şık]
📖 Gerekçe: [Mekanistik açıklama — neden doğru, neden diğerleri yanlış]
```

---

## ── TAMAMLANMA KONTROL LİSTESİ ───────────────────────────────

- [ ] Adım 0: E5 vektörleme + paralel namespace araması yapıldı
- [ ] Adım 0: Reranker (`bge-reranker-v2-m3`) uygulandı
- [ ] Adım 2: 20/80 High-Yield kimlik kartı üretildi
- [ ] Adım 3: Mekanizma kaskadı + katmanlı mimari var
- [ ] Adım 4: Ayırıcı Tanı Matrisi tablosu var
- [ ] Adım 5: DUS sınav perspektifi yazıldı
- [ ] Adım 6: Kavramlar çıkarıldı + `myppdfs/cikmis` tarandı
- [ ] Adım 7: Çıkmış soru kalite analizi yapıldı
- [ ] Adım 8: 5 yeni soru üretildi (2K/2O/1Z, cikmis kavramlarından farklı)
- [ ] Dil: Türkçe, emoji yok (sadece format ikonları), motivasyon klişesi yok

---

*Ders Çalışma Protokolü v2.0 | DUS Mentörü Projesi | 2026-04-27*
