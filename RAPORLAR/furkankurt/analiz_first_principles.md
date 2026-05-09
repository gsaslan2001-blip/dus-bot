# FIRST PRINCIPLES ANALİZİ — FURKAN KURT DUS SİSTEMİ

**Analiz Tarihi:** 4 Mayıs 2026
**Metodoloji:** First Principles Decomposition
**Analist:** Atlas (Claude Sonnet 4.6)

---

## 1. TEMEL BİLEŞENLERE AYIRMA

### 1.1 Sistemin Atomik Bileşenleri

Sistemi en küçük anlamlı birimlerine ayırdığımızda:

| # | Bileşen | Neden Var? | Zorunlu mu? |
|---|---------|-----------|-------------|
| A1 | Anki + FSRS | Uzun vadeli hafıza tutma | Evet — DUS bilgi hacmi için zorunlu |
| A2 | 90/20 Pomodoro | Odaklanmış çalışma blokları | Kısmen — alternatif zamanlama modelleri mevcut |
| A3 | Konu sıralaması (ROI bazlı) | Sınırlı zamanda maksimum puan | Evet — 27 hafta için kritik |
| A4 | AI kart üretimi (Claude API) | Yüksek hacimli, kaliteli kart üretimi | Kısmen — manuel üretim de mümkün ama yavaş |
| A5 | DUSBANKASI platformu | Özel soru bankası + vektör arama | Hayır — hazır soru bankaları mevcut |
| A6 | TickTick zaman bloklama | Günlük görev yönetimi | Hayır — takvim uygulaması yeterli |
| A7 | Google Sheets takip | Performans metrikleri | Kısmen — Anki istatistikleri yeterli olabilir |
| A8 | NotebookLM | Kavram netleştirme | Hayır — alternatif kaynaklar mevcut |
| A9 | Markmap zihin haritası | Görsel bilgi organizasyonu | Hayır — isteğe bağlı |
| A10 | Mekanizma-temelli öğrenme | Derin anlama + transfer | Evet — Furkan'ın bilişsel profili için zorunlu |

**Tespit:** 10 bileşenden sadece 3'ü (A1, A3, A10) gerçekten zorunlu. 4'ü isteğe bağlı. Bu, sistemin %40'ının "nice-to-have" olduğu anlamına gelir.

### 1.2 Her Bileşenin Varsayımları

**A1 (Anki + FSRS) varsayımları:**
- FSRS parametreleri doğru optimize edilmiş
- %89 hedef retention ile %91.1 fiili retention arasındaki fark zararsız
- 300 kart/gün review sürdürülebilir
- Kart kalitesi yeterince yüksek

**A3 (Konu sıralaması) varsayımları:**
- 480 soruluk analiz yeterince temsil edici
- ROI hesaplama formülü doğru ağırlıklandırılmış
- Konular arası bağımlılık yok (örn. Patoloji bilmeden Cerrahi çalışılabilir)

**A10 (Mekanizma-temelli öğrenme) varsayımları:**
- Tüm DUS konuları mekanizma bazlı öğrenmeye uygun
- Mekanizma kurulamayan konularda alternatif strateji var
- Bu yöntem zaman açısından verimli

---

## 2. NEDENSELLİK HARİTASI

### 2.1 Başarı Zinciri

```
Mekanizma Anlayışı → Kaliteli Kart Üretimi → Yüksek Anki Retention (%91.1)
                                                    ↓
Tutarlı Günlük Çalışma → Konu Tamamlama Hızı → Sınav Kapsamı Tamamlama
                                                    ↓
Soru Pratiği (DUSBANKASI) → Zayıf Nokta Tespiti → Hedefli Pekiştirme
                                                    ↓
                                            DUS İLK 10 BAŞARI
```

### 2.2 Başarısızlık Zinciri (En Kritik Yol)

```
Tetikleyici Olay → Odak Kaybı → Çalışma Tutarsızlığı → Konu Gecikmesi
                                                             ↓
Over-engineering Döngüsü ←────── Stres / Suçluluk ←───────┘
       ↓
Çalışma Saatlerinde Düşüş → Anki Review Birikmesi → Retention Düşüşü
                                                             ↓
                                                    HEDEFTEN UZAKLAŞMA
```

### 2.3 Bağımlılık Ağacı

```
DUS SKORU
├── [%40] Anki Retention ← Kart Kalitesi, Günlük Review Tutarlılığı
├── [%30] Konu Hakimiyeti ← Tamamlanan Konu Sayısı, Mekanizma Derinliği
├── [%20] Soru Pratiği ← DUSBANKASI/Quiz, Hata Analizi
└── [%10] Sınav Stratejisi ← Zaman Yönetimi, Soru Eleme
```

**Kritik bulgu:** Günlük Review Tutarlılığı, ağacın en tepesindeki 3 düğümü birden etkiliyor. Sistemin tek noktadan kırılma riski burada.

---

## 3. GİZLİ VARSAYIMLAR

### 3.1 Raporda Açıkça Yazılmayan Varsayımlar

| # | Gizli Varsayım | Risk Seviyesi | Gerçeklik Kontrolü |
|---|---|---|---|
| G1 | "Klinik rotasyon + DUS paralel yürütülebilir" | YÜKSEK | 5. sınıf stajı + DUS İlk 10 — birisi performans kaybedecek |
| G2 | "27 hafta, 8 ders için yeterli" | YÜKSEK | 8 ders × ortalama 15 ünite = 120 ünite. 27 hafta / 120 = ünite başına 1.6 gün. Tur 2 + soru pratiği için yetersiz. |
| G3 | "Mevcut Anki retention'ı (%91.1) gerçek öğrenmeyi yansıtıyor" | ORTA | %91.1 hedefin (%85) çok üzerinde. Kartlar fazla kolay veya interval yapısı hatalı olabilir. |
| G4 | "FSRS optimize edilmiş durumda" | ORTA | Raporda scheduling bug'dan bahsediliyor. Gerçekten tam optimize mi? |
| G5 | "İlk 10 hedefi, kurulan sistemle ulaşılabilir" | YÜKSEK | Sistem kalitesi ≠ sınav başarısı. 8000 kişilik havuzda ilk 10, üst %0.125 demek. |
| G6 | "DUSBANKASI geliştirme süresi, çalışma süresinden çalmıyor" | DÜŞÜK (açıkça risk olarak belirtilmiş) | Raporda over-engineering riski olarak tanımlanmış zaten. |
| G7 | "Sabah kliniği bilişsel yorgunluk yaratmaz" | ORTA | 07-11 arası yüksek biliş yükü, sonra 12-20 DUS. Recovery yok. |
| G8 | "Monk mode sürdürülebilir" | ORTA | Sosyal izolasyon uzun vadede mental sağlığı etkiler. 27 hafta uzun bir süre. |

### 3.2 En Tehlikeli Gizli Varsayım

**G2: "27 hafta yeterli" varsayımı.** Matematiksel olarak:

- 8 ders × ~15 ünite/ders = 120 ünite
- Her ünite: 1 gün ilk okuma + 1 gün kart üretimi + tekrar = minimum 3 gün/ünite
- 120 ünite × 3 gün = 360 gün → bu imkansız
- Gerçekçi plan: ünite başına 1 gün (sadece kritik kısımlar) = 120 gün ≈ 17 hafta
- Kalan 10 hafta: Tur 2 pekiştirme + soru pratiği
- **Bu sıkışık ama mümkün. Ancak hiç sapma payı yok.**

---

## 4. SIFIRDAN YENİDEN İNŞA

### 4.1 Neyi Korurdum?

1. **FSRS + Anki:** Uzun vadeli hafıza için en iyi araç. Aynen kalır.
2. **Mekanizma-temelli yaklaşım:** Furkan'ın bilişsel profiline uygun. Aynen kalır.
3. **ROI bazlı konu sıralaması:** Mantıklı ama veriyi güncellemek gerek.
4. **Claude API ile kart üretimi:** Verimli. Aynen kalır.

### 4.2 Neyi Farklı Yapardım?

**1. DUSBANKASI → Hazır soru bankasına geçiş:**
DUSBANKASI etkileyici bir mühendislik projesi. Ama İlk 10 hedefi olan bir adayın ihtiyacı olan şey, kendi soru bankasını geliştirmek değil, var olan soruları çözmek. 27 haftada sıfırdan platform geliştirmek yerine:
- Yayınevlerinin DUS soru bankalarını satın al
- Varsa DUS çıkmış soruları çöz
- DUSBANKASI geliştirmeyi sınav sonrasına ertele

**2. Araç sayısını 3'e indir:**
10 bileşenli sistem → 3 bileşenli sistem:
- Anki (hafıza)
- Soru bankası (pratik)
- Takvim (zaman yönetimi)
NotebookLM, Markmap, TickTick, Google Sheets → hepsi opsiyonel. Zaman emici.

**3. Klinik + DUS dengesini yeniden kur:**
Sabah 4 saat klinik + öğlen 8 saat DUS = 12 saat yüksek bilişsel yük. Sürdürülemez.
Alternatif: Klinik sonrası 1 saat zorunlu boşluk (yemek + yürüyüş). Sonra DUS.

**4. Tutarlılık için "asgari gün" tanımı:**
Her gün yapılması zorunlu minimum:
- 50 Anki review kartı (tam review değil, sadece minimum)
- 1 ünite ilerleme
- 10 soru çözümü
Bu seviye, düşük motivasyon günlerinde bile sistemi ayakta tutar.

### 4.3 Sıfırdan Sistem Mimarisi

```
KATMAN 1: ZORUNLU ÇEKİRDEK (her gün)
├── Anki Review: minimum 50 kart (ideal 300)
├── Konu İlerleme: 1 ünite/gün
└── Soru Pratiği: 10 soru/gün (ideal 50+)

KATMAN 2: DERİNLEŞTİRME (zaman kalırsa)
├── Zayıf nokta analizi
├── Mekanizma zinciri çizimi
└── Ek soru çözümü

KATMAN 3: SİSTEM BAKIMI (haftalık)
├── Haftalık review (Pazar akşamı 30 dk)
├── FSRS parametre kontrolü (aylık)
└── Konu takibi güncelleme

YASAKLI AKTİVİTELER (sınav sonrasına):
├── Yeni araç geliştirme
├── Prompt mühendisliği optimizasyonu
├── Platform feature ekleme
└── Sistem mimarisi yeniden tasarımı
```

---

## 5. TEMEL GERÇEKLER vs STRATEJİK TERCİHLER

### 5.1 Doğrulanabilir Temel Gerçekler

| Gerçek | Kanıt |
|--------|-------|
| 10.851 Anki kartı var | Anki istatistikleri |
| %91.1 retention oranı | Anki istatistikleri |
| 5 ders tamamlandı | İlerleme takibi |
| 27 hafta kaldı | Takvim |
| Haftalık ~35-40 saat çalışma potansiyeli var | Klinik sonrası zaman |
| 1.011+ saat çalışma yapılmış | Pomodoro kayıtları |
| Tarihsel tutarlılık %32-62 | Google Sheets verisi |

### 5.2 Stratejik Tercihler (Tartışmaya Açık)

| Tercih | Alternatifi | Değerlendirme |
|--------|-------------|---------------|
| DUSBANKASI geliştirmek | Hazır soru bankası kullanmak | Riskli tercih — zaman maliyeti yüksek |
| 90/20 Pomodoro | 50/10 veya 25/5 | Kişisel tercih, veriyle desteklenmeli |
| Mekanizma-önce yaklaşımı | Konu anlatımı-önce | Furkan için doğru tercih |
| Monk mode | Dengeli sosyal yaşam | 27 hafta için riskli |
| FSRS %85 hedef | Daha yüksek hedef | Mevcut %91.1 zaten üzerinde |
| Konu sırası (Cerrahi erken) | Farklı sıralama | Veriye dayalı, mantıklı |

### 5.3 Sahte Kesinlikler

Bunlar gerçek gibi sunulan ama aslında tahmin olan ifadeler:

- "İlk 10 hedefi" — 8.000 kişilik havuzda ilk 10, istatistiksel olarak uç değer. Sistem kalitesiyle garantilenemez.
- "480 soru analizi yeterli" — 4 dönem, değişen sınav pattern'lerini tam yansıtmayabilir.
- "%91.1 retention iyi" — Aslında hedefin çok üzerinde, bu bir sorun işareti olabilir.

---

## 6. KRİTİK BULGU VE ÖNERİLER

### 6.1 En Kritik 3 Bulgu

**Bulgu 1: Sistem over-engineered.**
10 araçlı sistem, 3 araçlık işi yapıyor. Her ek araç: bakım süresi, bilişsel yük, dikkat dağıtma potansiyeli.

**Bulgu 2: Zaman matematiği tutmuyor.**
8 ders × 15 ünite = 120 ünite. 27 hafta = 189 gün. Ünite başına 1.5 gün. Tur 1 + Tur 2 + soru pratiği için bu süre kritik derecede sıkışık. Hiç fire vermeden ilerlemek gerekiyor ki tarihsel tutarlılık %32-62 iken bu riskli.

**Bulgu 3: Tutarlılık, sistemin tek noktadan kırılma riski.**
Altyapı mükemmel; icraat dalgalı. İlk 10 hedefi, altyapı kalitesiyle değil, günlük tutarlılıkla belirlenecek.

### 6.2 Aksiyon Önerileri (Öncelikli)

1. **[BUGÜN] Araç diyeti:** NotebookLM, Markmap, Google Sheets'i dondur. Sadece Anki + Soru Bankası + Takvim kalsın.
2. **[BUGÜN] DUSBANKASI dondurma:** Sınav sonrasına kadar yeni feature ekleme. Sadece mevcut haliyle soru çözmek için kullan.
3. **[BU HAFTA] Gerçekçi zaman planı:** 8 ders için ünite ünite, hafta hafta tamamlama takvimi çıkar. Sapma payı bırak.
4. **[BU HAFTA] Asgari gün standardı:** 50 kart + 1 ünite + 10 soru = kriz günlerinde dahi yapılacak minimum.
5. **[SÜREKLİ] FSRS denetimi:** %85 hedef, %91.1 fiili retention farkını araştır. Kart zorluğu mu düşük, interval mi kısa?

### 6.3 First Principles Özet

> Sistemin özü 3 şeydir: **Anki (hafıza) + Konu Okuma (girdi) + Soru Çözme (çıktı testi).**
> Geri kalan her şey — DUSBANKASI, NotebookLM, Markmap, TickTick, Google Sheets — bu üçünü desteklediği sürece değerli, desteklemediği an yüktür.
> 27 hafta, dünyanın en iyi sistemiyle değil, en tutarlı icraatla kazanılır.

---

*First Principles Analysis — Atlas | 4 Mayıs 2026*
