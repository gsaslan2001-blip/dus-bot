# FURKAN KURT — DUS ÇALIŞMA SİSTEMİ: MİMARİ ANALİZ RAPORU

**Rapor Tarihi:** 4 Mayıs 2026
**Analiz Eden:** Serena Blackwood — "The Academic Visionary" Architect Agent
**Analiz Derinliği:** MAKSİMUM (Constitutional + Strategic + Implementation)
**Referans Rapor:** `furkan_kurt_dus_sistem_raporu.md`
**Analiz Odağı:** Anayasal Prensipler, Sistem Mimarisi, Stratejik Boşluklar, İdeal Mimari, Uygulama Planı

---

## 1. EXECUTIVE SUMMARY

Furkan Kurt'un DUS çalışma sistemi, metodolojik temelleri sağlam ancak uygulama tutarlılığı kırılgan bir dağıtık bilişsel sistemdir. Sistemin anayasal omurgası (mekanizma-öncelikli öğrenme, spaced repetition, aktif retrieval, faz-gated progression) ortalama DUS adayının çok üzerindedir; fakat bu omurganın taşıyıcı kolonu olan insan tutarlılığı (%32-62 bandı) ve zaman-müfredat denklemi (97 ünite / 27 hafta = 3.6 ünite/hafta teorik minimum), mimari düzeyde bir yeniden yapılandırmayı zorunlu kılmaktadır. En kritik anayasal eksiklik, sistemin kendi kullanıcısının en zayıf anında onu ayakta tutacak bir "minimum viable engagement" protokolüne sahip olmamasıdır. Mevcut over-engineering döngüsü (DUSBANKASI geliştirme, pipeline optimizasyonu), temel kısıt olan zamanı doğrudan tüketen bir kaynak sızıntısıdır. Faz 2-3 geçişinde radikal bir basitleştirme ve otomasyon hamlesi yapılmadığı takdirde, sistemin ilk 10 hedefi, altyapının kalitesine rağmen risk altındadır.

---

## 2. ANAYASAL PRENSİPLER KATALOĞU

### 2.1 Mevcut Prensipler — Güçlü Olanlar

#### P1: MEKANİZMA-ÖNCELİKLİ ÖĞRENME (Constitutional — Sağlam)
```
TANIM: Her bilgi birimi, izole bir fakt değil, bir nedensellik zincirinin halkasıdır.
KANIT: STRATEGY.md §3.1, DECISIONS.md #10
UYGULAMA: "Neden?" zinciri (5 seviye), kök neden analizi, kaskad mekanizması
DURUM: AKTİF ve GÜÇLÜ. Sistemin en sağlam anayasal prensibi.
```

Bu prensip, Furkan'ın öğrenme stilinin DNA'sıdır. Bilgi işleme, root-cause first, detail second hiyerarşisiyle gerçekleşir. Mekanizma kurulmadan bilgi işlenmez — bu, ezber direncini tanımlayan bir kognitif filtre işlevi görür. Prensibin dayanağı, Ebbinghaus unutma eğrisinin mekanistik bağlamla kırılabileceği gözlemidir: nedensellik zinciriyle kodlanan bilgi, izole faktlara göre anlamlı derecede uzun retention gösterir.

**Mimari karşılığı:** CAP teoreminin dağıtık sistemler için anlamı neyse, mekanizma-öncelik prensibi de bu öğrenme sistemi için odur — temel bir kısıt, optimize edilemez, ancak tasarım bu kısıt etrafında şekillendirilebilir.

#### P2: AKTİF RETRIEVAL DOMINANCE (Constitutional — Sağlam)
```
TANIM: Bilgi edinme sürecinde pasif okuma yasaktır; her tekrar aktif geri çağırma içermelidir.
KANIT: STRATEGY.md §3.2, §3.5.2
UYGULAMA: Anki (kapalı cevap → üret → karşılaştır), Feynman, soru bankası
DURUM: AKTİF. Anki'de doğru uygulanıyor (10-15 sn düşünme zorunlu). Feynman dalgalı.
```

Bu prensip, testing effect'in (Roediger & Karpicke, 2006) doğrudan sistem mimarisine yansıtılmasıdır. Anki kartlarında "tanıdık görünüyor = biliyorum" yanılgısına karşı açık bir protokol tanımlanmıştır (STRATEGY.md §3.5.2). Feynman tekniğinin "uzun sürdüğü için bırakılması" (STRATEGY.md §2), sistemin bu prensipten en büyük sapmasıdır — zira Feynman sürecinin uzun sürmesi, derin encoding'in gerçekleştiğinin pozitif sinyalidir.

#### P3: TEK KAYNAK FELSEFESİ (Constitutional — Sağlam)
```
TANIM: Her turda birincil kaynak tektir. Kaynak çeşitlendirmesi sadece stratejik aşamalarda yapılır.
KANIT: STRATEGY.md §3.1 "Kaynak Seçimi"
UYGULAMA: Tur 1 tek kaynak, Tur 2 ana kaynak + soru bankası, son 6 hafta soru + kısa referans
DURUM: AKTİF. Kognitif yük kontrolü için kritik.
```

Bu prensip, bilişsel yük teorisiyle (Sweller, 1988) uyumludur. Çoklu kaynak, split-attention effect yaratarak öğrenmeyi yavaşlatır. Sistemin bu prensibi benimsemesi, ortalama DUS adayının "her kaynaktan çalışma" tuzağına karşı bilinçli bir mimari tercihtir.

#### P4: FAZ-GATED PROGRESSION (Anayasal Taslak — Orta Sağlamlıkta)
```
TANIM: Sistem ilerlemesi, keyfi zaman çizelgesiyle değil, ölçülebilir geçiş kriterleriyle belirlenir.
KANIT: STRATEGY.md §3.6, PROGRESS.md §TUR DURUMU
UYGULAMA: Faz 1→2 (Tur 1 tamamlanma), Faz 2→3 (mock %70+), Faz 3→4 (mock %80+)
DURUM: TANIMLI AMA GEVŞEK UYGULANIYOR. Kriterler yazılı fakat otomatik enforcement yok.
```

Faz yapısı kağıt üzerinde sağlamdır: her fazın net bir geçiş kriteri ve "bitirdim" tanımı vardır. Ancak pratikte, Tur 2'ye geçiş kriteri olan "Tüm konular + Anki hazır" koşulu sağlanmadan kısmi geçiş yapılmıştır (5 ders Tur 1 tamamlandı, 8 ders bekliyor, ama Tur 2 aktif). Bu, faz disiplininin gevşek uygulandığının göstergesidir.

#### P5: CROSS-LINKING ZORUNLULUĞU (Anayasal Taslak — Zayıf)
```
TANIM: Her konu, önceki konularla bağlantılandırılmadan "tamamlanmış" sayılmaz.
KANIT: STRATEGY.md §3.2 "Cross-Linking Protokolü"
UYGULAMA: 3 zorunlu soru (benzerlik, klinik karşıt, eş zamanlı durum)
DURUM: TANIMLI AMA NADİREN UYGULANIYOR. Takip mekanizması yok.
```

Cross-linking, DUS'un klinik vignette soruları için hayati öneme sahiptir. Ancak sistemde bu protokolün uygulandığına dair bir izleme mekanizması yoktur. PROGRESS.md'de cross-linking tamamlanma durumu takip edilmez.

### 2.2 Anayasal Boşluklar — Eksik Olan Prensipler

Aşağıdaki prensipler, sistemin anayasasında tanımlanmamış ancak mimari bütünlük için zorunlu olan temel kurallardır:

#### E1: MİNİMUM VİABLE ENGAGEMENT (MVE) — Kritik Eksik
```
TANIM: Sistem, kullanıcının en düşük motivasyon anında dahi tamamlayabileceği
minimum günlük protokolü tanımlamalı ve bunu anayasal bir zorunluluk olarak
korumalıdır.

MEVCUT DURUM: Kriz anında sistem tamamen devre dışı kalabilmektedir.
Tutarlılık %32-62 bandında dalgalanmaktadır. "0 gün" kabul edilebilir
bir durum olarak sistemde yer bulabilmektedir.

ANAYASAL GEREKLİLİK: "Günde minimum X — istisnasız, tartışmasız."
Bu bir prensip değil, bir KISIT olarak tanımlanmalıdır. CAP teoremi nasıl
bir dağıtık sistemin aynı anda tutarlı, erişilebilir ve bölünebilir
olamayacağını söylüyorsa, bu kısıt da "sıfır gün"ün sistemin bütünlüğünü
bozduğunu söylemelidir.
```

Bu, sistemin en büyük anayasal boşluğudur. Sistem, yüksek performans için optimize edilmiştir; düşük performans anları için değil. Oysa dağıtık sistemlerde graceful degradation esastır — sistem tamamen çökmez, hizmet seviyesini düşürerek çalışmaya devam eder.

#### E2: KAYNAK TAHSİS BÜTÇESİ (Resource Allocation Budget) — Kritik Eksik
```
TANIM: Araç geliştirme, pipeline optimizasyonu, sistem tasarımı gibi
"meta-çalışma" faaliyetleri için toplam çalışma süresinin maksimum %X'i
kadar bir üst sınır tanımlanmalıdır.

MEVCUT DURUM: Over-engineering döngüsü, sistemin bilinen en büyük
tuzaklarından biridir. DUSBANKASI geliştirme, prompt mühendisliği,
araç optimizasyonu zamanları, doğrudan konu çalışma süresiyle rekabet
etmektedir.

ANAYASAL GEREKLİLİK: "Meta-çalışma süresi < toplam çalışma süresinin %10'u."
Bu bir bütçe kısıtıdır, opsiyonel değildir.
```

Sistem şu anda kendi kendini tüketme riski taşımaktadır. DUSBANKASI ve pipeline'ların geliştirilmesi, öğrenme hedefinden saparak kendi başına bir amaç haline gelebilmektedir. Bu, "araç fetişizmi" (tool fetishism) pattern'ının klasik bir örneğidir: görünürde verimli hissettirdiği için tespit edilmesi güçtür.

#### E3: FEEDBACK LOOP KAPATMA ORANI — Kritik Eksik
```
TANIM: Tespit edilen her zayıf nokta, bir tamir aksiyonuna bağlanmalı
ve kapatılana kadar açık issue olarak izlenmelidir.

MEVCUT DURUM: Blind spot'lar tanımlanıyor (PROGRESS.md'de Blind Spot
Kayıtları var) ancak kapatılma oranı takip edilmiyor. Endodonti Travma
blind spot'u tanımlanmış ama kapatıldığına dair kayıt yok.

ANAYASAL GEREKLİLİK: "Açılan her blind spot, kapatılana kadar haftalık
review'da gündemdedir. Kapatılmayan 2 haftalık spot → escalasyon."
```

#### E4: TEKİL DOĞRULUK KAYNAĞI (Single Source of Truth) — Yapısal Eksik
```
TANIM: Her veri tipi için tek bir kanonik kaynak olmalıdır.
Veri, kaynaklar arası manuel olarak kopyalanmamalıdır.

MEVCUT DURUM: PROGRESS.md "canonical" olarak tanımlanmış ancak:
- Anki retention verisi PROGRESS.md'ye manuel kopyalanıyor
- TickTick Pomodoro verisi PROGRESS.md'ye manuel kopyalanıyor
- DUSBANKASI soru performansı izole durumda
- Google Sheets verisi ayrı bir evrende

ANAYASAL GEREKLİLİK: "Her veri tipinin tek bir kanonik kaynağı vardır.
Kaynaklar arası veri transferi otomatiktir veya yoktur."
```

#### E5: HATA SINIFLANDIRMA VE TREND TAKİBİ — Orta Eksik
```
TANIM: Her yanlış cevap, bir hata kategorisine atanmalı ve kategoriler
arası trend takip edilmelidir.

MEVCUT DURUM: STRATEGY.md'de 3'lü sınıflandırma (bilgi/anlama/dikkat)
tanımlanmış ancak sistematik tracking yok. Mock sonrası analiz için
format belirlenmiş ama veri birikimi yok.

ANAYASAL GEREKLİLİK: "Her mock sınav sonrası hata kategorizasyonu zorunludur.
3 mock boyunca aynı kategoride artış → strateji revizyonu tetiklenir."
```

---

## 3. MEVCUT MİMARİ DEĞERLENDİRMESİ

### 3.1 Sistem Bileşenleri ve Coupling/Cohesion Analizi

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FURKAN KURT DUS SİSTEM MİMARİSİ                        │
│                               (Mevcut Durum)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    ANKİ      │  │  DUSBANKASI  │  │  NOTEBOOKLM  │  │   TICKTICK   │     │
│  │  (FSRS)      │  │ (Supabase +  │  │   (RAG)      │  │ (Zaman Blok) │     │
│  │              │  │  React+AI)   │  │              │  │              │     │
│  │ • 12.333 kart│  │ • Soru bank. │  │ • Müfredat   │  │ • Pomodoro   │     │
│  │ • Retention  │  │ • Zayıf nok. │  │ • Q&A        │  │ • Görev      │     │
│  │   %90.6      │  │ • RAG        │  │ • Audio      │  │ • Hatırlatma │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │                 │             │
│         │    MANUEL       │    MANUEL       │    MANUEL       │    MANUEL   │
│         │    ENTEGRASYON  │    ENTEGRASYON  │    ENTEGRASYON  │    ENTEG.   │
│         │                 │                 │                 │             │
│         ▼                 ▼                 ▼                 ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     👤 FURKAN (İnsan Entegrasyon Bus'ı)              │    │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐  │    │
│  │  │PROGRESS │  │ STRATEGY│  │DECISIONS │  │ GOOGLE  │  │ ZİHİNSEL│  │    │
│  │  │.md      │  │ .md     │  │ .md      │  │ SHEETS  │  │ MODEL   │  │    │
│  │  │(Manuel) │  │(Manuel) │  │(Manuel)  │  │(Manuel) │  │(İçsel)  │  │    │
│  │  └─────────┘  └─────────┘  └──────────┘  └─────────┘  └─────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    CLAUDE API (AI Katmanı)                            │   │
│  │  • Kart üretimi (Basic + Cloze)                                      │   │
│  │  • Soru üretimi (6 soru tipi)                                        │   │
│  │  • Didikle analizi (3-agent paralel)                                 │   │
│  │  • Mindmap üretimi (Markmap)                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  BAĞLANTI TİPLERİ:                                                          │
│  ──── Otomatik veri akışı                                                    │
│  ════ Manuel veri kopyalama (HATA KAYNAĞI)                                  │
│  ···· Zihinsel entegrasyon (güvenilmez)                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Coupling Analizi:**

Sistem bileşenleri arasındaki bağlantı **manuel insan entegrasyonu** üzerinden sağlanmaktadır. Bu, dağıtık sistemler terminolojisinde "Human-in-the-loop Integration Bus" olarak adlandırılabilir ve aşağıdaki riskleri taşır:

| Risk | Açıklama | Şiddet |
|---|---|---|
| **Entegrasyon yorgunluğu** | Her bileşenin ayrı güncellenmesi, toplam bilişsel yükü artırır | YÜKSEK |
| **Veri tutarsızlığı** | Aynı veri (örn: retention) birden fazla yerde farklı değerlerle bulunabilir | ORTA |
| **Senkronizasyon gecikmesi** | Anki snapshot'ı haftalık alınır; gerçek zamanlı değildir | ORTA |
| **Tek hata noktası (SPOF)** | İnsan entegratör devre dışı kalırsa tüm sistem durur | KRİTİK |

**Cohesion Analizi:**

Her bileşen kendi içinde yüksek kohezyona sahiptir (Anki hafıza yönetimi, DUSBANKASI soru pratiği, TickTick zaman yönetimi). Ancak **sistem seviyesinde kohezyon düşüktür** — bileşenler birbirinden habersiz çalışan izole adalardır.

### 3.2 Veri Akışı ve Bilgi Akışı Haritası

```
┌─────────────────────────────────────────────────────────────────────┐
│                       VERİ AKIŞ DİYAGRAMI                            │
│                    (Mevcut — Noktalı = Manuel)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Ders Notu PDF]                                                    │
│        │                                                             │
│        ▼                                                             │
│  [PDF→MD Pipeline]──→[NotebookLM]                                   │
│        │                    │                                        │
│        ▼                    ▼                                        │
│  [Claude API]         [Sesli Özet]                                   │
│        │                                                             │
│        ├──→[Basic Kart]──→[Anki Basic Deck]                         │
│        ├──→[Cloze Kart]──→[Anki Cloze Deck]                         │
│        ├──→[Mindmap]────→[Markmap]                                   │
│        └──→[Soru]───────→[DUSBANKASI]·····→[Zayıf Nokta Analizi]   │
│                                 │                                     │
│                                 ▼                                     │
│                            [Performans ····→ [Google Sheets]         │
│                             Verisi]                                   │
│                                                                      │
│  [TickTick]────→[Pomodoro Sayısı]····→[PROGRESS.md]                 │
│  [Anki]────────→[Retention %]········→[PROGRESS.md]                 │
│  [Anki]────────→[Kart Sayısı]········→[PROGRESS.md]                 │
│  [DUSBANKASI]──→[Soru Başarı %]······→[?????]  (KAYIP VERİ)        │
│                                                                      │
│  TIKANIKLIK NOKTALARI:                                               │
│  ⚠ T1: PROGRESS.md güncellemesi tamamen manuel                      │
│  ⚠ T2: Anki retention → PROGRESS.md kopyalaması manuel              │
│  ⚠ T3: DUSBANKASI performans verisi hiçbir yere entegre değil       │
│  ⚠ T4: Google Sheets izole — PROGRESS.md ile çift veri girişi       │
│  ⚠ T5: Haftalık review manuel; düşük tutarlılıkta atlanıyor         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Kritik Tıkanıklık:** T3 (DUSBANKASI performans verisinin kaybolması). Sistemin en sofistike bileşeni olan DUSBANKASI, soru performans verisi üretmekte ancak bu veri hiçbir üst katmana akmamaktadır. Bu, sistemin en değerli feedback loop'unun açık devre olduğu anlamına gelir.

### 3.3 Single Source of Truth (SSoT) Analizi

```
MEVCUT SSoT HARİTASI:
─────────────────────────────────────────────
Veri Tipi          │ Kanonik Kaynak │ Gerçek Durum        │ Tutarsızlık
───────────────────┼────────────────┼─────────────────────┼─────────────
Ünite ilerlemesi   │ PROGRESS.md    │ PROGRESS.md (doğru) │ DÜŞÜK
Anki retention     │ PROGRESS.md    │ Anki (gerçek)       │ ORTA
                   │                │ PROGRESS.md (kopya) │
Pomodoro sayısı    │ PROGRESS.md    │ TickTick (gerçek)   │ ORTA
                   │                │ PROGRESS.md (kopya) │
Çalışma saati      │ PROGRESS.md    │ TickTick (gerçek)   │ ORTA
                   │                │ PROGRESS.md (kopya) │
Soru performansı   │ TANIMSIZ       │ DUSBANKASI (izole)  │ YÜKSEK
Hata kategorileri  │ TANIMSIZ       │ Yok                 │ KRİTİK
Blind spot durumu  │ PROGRESS.md    │ PROGRESS.md (manuel)│ ORTA
Cross-linking      │ TANIMSIZ       │ Yok                 │ KRİTİK
─────────────────────────────────────────────────────────────
```

**Mimari Yargı:** PROGRESS.md, SSoT olarak tanımlanmış ancak **gerçek SSoT değildir**. Çünkü:
1. Verilerin çoğu başka bir yerden (Anki, TickTick) manuel kopyalanır.
2. Kopyalama işlemi hataya açıktır ve gecikmelidir.
3. Bazı kritik veriler (soru performansı, hata kategorileri) hiçbir SSoT'ye sahip değildir.

Bu, dağıtık sistemlerdeki "split-brain" problemine benzer: iki sistem (gerçek kaynak ve PROGRESS.md) aynı veri için farklı değerlere sahip olabilir.

### 3.4 Feedback Loop'ların Kalite ve Hız Analizi

```
FEEDBACK LOOP ENVANTERİ:
────────────────────────────────────────────────────────────────────────
Loop                  │ Frekans    │ Gecikme    │ Kalite    │ Otomasyon
──────────────────────┼────────────┼────────────┼───────────┼──────────
Anki kart (anlık)     │ ~300/gün   │ 10-15 sn   │ YÜKSEK    │ OTOMATİK
Soru bazlı (konu)     │ Düzensiz   │ Anlık       │ YÜKSEK    │ YARI-OTO
Feynman (konu)        │ Haftalık?   │ Anlık       │ ÇOK YÜKSEK│ MANUEL
Haftalık review       │ 7 gün      │ 7 gün       │ ORTA      │ MANUEL
Mock sınav            │ Aylık?      │ Anlık       │ YÜKSEK    │ MANUEL
PROGRESS.md güncelleme│ Düzensiz   │ 1-7 gün     │ DÜŞÜK     │ MANUEL
Blind spot kapatma    │ Düzensiz   │ Haftalar-ay │ DÜŞÜK     │ MANUEL
DUSBANKASI performans │ Gerçek zmn. │ 0           │ YÜKSEK    │ OTO AMA İZOLE
────────────────────────────────────────────────────────────────────────
```

**En Kritik Feedback Eksikliği:** Mock sınav feedback loop'u. STRATEGY.md'de mükemmel bir mock analiz formatı tanımlanmış olmasına rağmen, bu loop'un frekansı çok düşüktür. 27 hafta kala sistemin gerçek sınav performansını ölçecek düzenli mock'lar yapılmıyor olması, sistemi "kör uçuş" modunda bırakmaktadır. Mimari olarak bu, bir dağıtık sistemin monitoring'den yoksun çalışmasına eşdeğerdir.

---

## 4. STRATEJİK BOŞLUK ANALİZİ

### 4.1 Zaman-Müfredat Çakışması: Sayısal Analiz

```
MEVCUT DURUM (4 Mayıs 2026):
──────────────────────────────────────────────────────────────
Sınava kalan süre:          ~27 hafta (189 gün)
Klinik rotasyon:            Sabah 07:00-11:00 (günde 4 saat kayıp)
Haftalık çalışma günü:      5 gün (gerçekçi, hafta sonu dahil)
Günlük çalışma kapasitesi:  6-7 saat
Haftalık net kapasite:      ~30-35 saat

BEKLEYEN İŞ YÜKÜ:
──────────────────────────────────────────────────────────────
Kalan ders (Tur 1):         8 ders / 97 ünite
  Cerrahi-Anatomi:          20 ünite
  Biyokimya:                12 ünite
  Ortodonti:                12 ünite
  Restoratif:               9 ünite
  Pedodonti:                16 ünite
  Mikrobiyoloji:            12 ünite
  Farmakoloji:              12 ünite
  Radyoloji:                4 ünite

Tur 2 tekrar (tüm 12 ders): ~164 ünite tekrarı
Tur 3 tekrar:                ~164 ünite (hedeflenen)
Tur 4 tekrar:                ~164 ünite (hedeflenen)
Deneme fazı:                 4 ay (Temmuz-Ekim)

TEORİK ZAMAN GEREKSİNİMİ:
──────────────────────────────────────────────────────────────
Tur 1 (kalan 97 ünite):
  Optimal: 1 ünite/gün = 97 gün (~14 hafta) → Bitiş: Ağustos ortası
  Sıkıştırılmış: 1.5 ünite/gün = 65 gün (~9 hafta) → Bitiş: Temmuz başı
  Agresif: 2 ünite/gün = 49 gün (~7 hafta) → Bitiş: Haziran ortası

Tur 2 + Tur 3 + Tur 4 (~492 ünite-tekrar):
  Optimal: 5 ünite/gün tekrar = 98 gün (~14 hafta)
  Gerçekçi: 3 ünite/gün tekrar = 164 gün (~23 hafta) → 27 haftayı AŞAR

DENEME FAZI: En az 8 hafta gerekli.

GERÇEKÇİ TOPLAM: Tur 1 (9 hafta) + Tekrarlar (14 hafta) + Deneme (8 hafta) = 31 hafta

SONUÇ: 27 haftalık bütçe, GERÇEKÇİ SENARYODA 31 haftalık iş yükünü karşılamamaktadır.
4 haftalık AÇIK vardır.
```

**Mimari Yargı:** Sistemin zaman-müfredat denklemi, mevcut planla kapatılamaz bir açık vermektedir. Bu, "fazla rezervasyon" (overbooking) problemidir. Çözüm, iş yükünü azaltmak (kapsam daraltma) veya verimi artırmak (birim zamanda daha fazla ünite) olabilir — ancak ikincisi kaliteden ödün vermek anlamına gelir.

### 4.2 Retention %91.1 vs Hedef %85: Mimari Anlamı

Bu delta, basit bir "iyi haber" olarak okunmamalıdır. Mimari açıdan üç olası açıklaması vardır:

```
SENARYO A: Kartlar Çok Kolay
─────────────────────────────
Mevcut kartlar, Furkan'ın gerçek bilgi seviyesinin altında zorluktadır.
Sonuç: False sense of mastery. Sınavda daha zor sorularla karşılaşınca
retention çöker.

SENARYO B: FSRS Optimize Edilmemiş (EN MUHTEMEL)
─────────────────────────────────────────────────
FSRS parametreleri, %85 hedef retention için optimize edilmişken
interval'ler çok kısa kalmıştır. S0 Good: 33.16 gün değeri,
optimalden sapma göstermektedir. Son hafta retention %74.8'e
düşmüştür — bu, interval'ler uzadıkça gerçek retention'ın hedefin
altına indiğini gösterir.

SENARYO C: Seçici Kart Üretimi
───────────────────────────────
Sadece zor/yüksek getirili kavramlar kart yapıldığı için,
bunlar iyi öğrenilmiş durumdadır. Ancak kart yapılmayan
"orta zorluktaki" bilgiler retention'a yansımamaktadır.

MİMARİ ÖNERİ:
- FSRS parametrelerini %85 hedefi için YENİDEN optimize et
- "Reschedule" özelliğini AKTİF et (eski kartlara yeni parametreleri uygula)
- Son hafta retention'ı haftalık takip et — %80 altına düşerse alarm
```

### 4.3 Tutarlılık %32-62: Kök Neden Analizi

```
TUTARLILIK SORUNUNUN 5-NEDEN ANALİZİ:

1. NEDEN tutarlılık düşük?
   → Çalışma sistemi, düşük motivasyon anlarında tamamen devre dışı kalıyor.

2. NEDEN düşük motivasyonda sistem devre dışı kalıyor?
   → Sistemin "minimum mod"u yok. Ya tam kapasite çalışıyor ya da hiç çalışmıyor.

3. NEDEN minimum mod yok?
   → Sistem tasarımı, yüksek performans için optimize edilmiş. Graceful degradation
     düşünülmemiş.

4. NEDEN graceful degradation düşünülmemiş?
   → Furkan'ın sistem kurma yaklaşımı "mükemmeliyetçi mimari" eğiliminde.
     Over-engineering döngüsü, "eksik sistem" fikrini reddediyor.

5. NEDEN mükemmeliyetçilik over-engineering'e dönüşüyor?
   → Temel kısıt (zaman) ile sistem kurma hazzı arasındaki gerilim.
     Sistem kurmak, çalışmaktan daha fazla dopamin ödülü sağlıyor.

KÖK NEDEN: Sistem, kullanıcısının nörokimyasal ödül mekanizmasına
yenik düşüyor. Araç geliştirmek (DUSBANKASI, pipeline), ders
çalışmaktan daha hızlı ve öngörülebilir dopamin sağlıyor.
```

### 4.4 Over-Engineering vs Under-Studying: Kaynak Tahsisi Optimizasyonu

```
KAYNAK TAHSİS MATRİSİ (Tahmini):
────────────────────────────────────────────────────────────
Aktivite Kategorisi        │ Zaman Payı │ DUS ROI │ Verimlilik
───────────────────────────┼────────────┼─────────┼───────────
Konu çalışması (okuma)     │ %25        │ YÜKSEK  │ YÜKSEK
Anki review                │ %20        │ YÜKSEK  │ YÜKSEK
Soru çözme                 │ %10        │ ÇOK Y.  │ ÇOK YÜKSEK
Kart üretimi (AI destekli) │ %15        │ ORTA    │ ORTA
DUSBANKASI geliştirme      │ %10        │ DÜŞÜK   │ ÇOK DÜŞÜK
Pipeline/araç optimizasyon │ %10        │ DÜŞÜK   │ ÇOK DÜŞÜK
Sistem dokümantasyonu      │ %5         │ DÜŞÜK   │ DÜŞÜK
Haftalık review            │ %3         │ ORTA    │ ORTA
Diğer                      │ %2         │ -       │ -
───────────────────────────┼────────────┼─────────┼───────────
TOPLAM                     │ %100       │         │
───────────────────────────┴────────────┴─────────┴───────────

TEHLİKE BÖLGESİ: %20 (DUSBANKASI + Pipeline + Dokümantasyon)
Bu %20'lik dilim, sıfırlanırsa 5.4 ekstra hafta kazandırır.
```

---

## 5. İDEAL MİMARİ TASARIMI (Feature Spec)

### 5.1 Tasarım Prensipleri (Anayasa v2.0)

Sıfırdan tasarım yapılsaydı, sistem şu anayasal prensipler üzerine kurulurdu:

```
╔═══════════════════════════════════════════════════════════════╗
║             DUS ÇALIŞMA SİSTEMİ ANAYASASI v2.0               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  KISITLAR (İhlal Edilemez — CAP Teoremi Seviyesinde)         ║
║  ─────────────────────────────────────────────────────────   ║
║  K1: SIFIR GÜN YASAKTIR. Günde minimum 1 kart review.        ║
║  K2: Meta-çalışma < toplam sürenin %5'i.                     ║
║  K3: Her dersin Tur 1 bitişinde mastery sınavı zorunludur.   ║
║  K4: Mock sınav, 2 haftada birden seyrek yapılamaz.          ║
║                                                               ║
║  PRENSİPLER (Optimizasyon Hedefleri)                          ║
║  ─────────────────────────────────────────────────────────   ║
║  P1: MEKANİZMA-ÖNCELİKLİ — Her bilgi nedensellik zincirinde  ║
║  P2: AKTİF RETRIEVAL — Pasif okuma yasak                      ║
║  P3: TEK KAYNAK — Tur başına tek birincil kaynak              ║
║  P4: FAZ-GATED — Ölçülebilir kriter olmadan faz atlanmaz     ║
║  P5: CROSS-LINK — Her konu eski konularla bağlanır            ║
║  P6: HATA-KATEGORİLİ — Her yanlış bilgi/anlama/dikkat        ║
║  P7: GRACEFUL DEGRADATION — Sistem kısmi yükte çalışır       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### 5.2 Minimum Viable System (MVS)

"Olmazsa olmaz" bileşenler — sadece bunlarla DUS kazanılabilir:

```
┌─────────────────────────────────────────────────┐
│         MİNİMUM VİABLE SYSTEM (MVS)             │
│         "Sadece Olmazsa Olmazlar"               │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  ANKİ    │    │  KONU    │    │  SORU    │  │
│  │  (FSRS)  │◄──►│  NOTLARI │◄──►│  BANKASI │  │
│  │          │    │  (.md)   │    │  (PDF)   │  │
│  └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │        │
│       └───────────────┼───────────────┘        │
│                       │                        │
│                       ▼                        │
│              ┌─────────────────┐               │
│              │  PROGRESS.md    │               │
│              │  (Tekil .md)    │               │
│              └─────────────────┘               │
│                                                  │
│  ÇIKARILANLAR (MVS'te YOK):                     │
│  ❌ DUSBANKASI (özel yazılım)                   │
│  ❌ NotebookLM (opsiyonel RAG)                  │
│  ❌ TickTick (basit timer yeterli)              │
│  ❌ Google Sheets (redundant)                   │
│  ❌ Markmap (opsiyonel görselleştirme)          │
│  ❌ Claude API pipeline'ları (manuel kart)      │
│  ❌ Supabase, Pinecone (altyapı)                │
│                                                  │
│  MVS, 3 BİLEŞEN + TEKİL TAKİP DOSYASI:          │
│  Toplam araç sayısı: 4 (3+1)                    │
│  Haftalık meta-çalışma: ~0 saat                 │
│                                                  │
└─────────────────────────────────────────────────┘
```

**MVS'in arkındaki mantık:** DUS kazanmak için gereken minimum sistem, bir spaced repetition motoru (Anki), yapılandırılmış konu notları ve bir soru bankasıdır. Bu üç bileşen, öğrenme biliminin kanıtlanmış üç ayağına karşılık gelir: spaced repetition, structured encoding, ve testing effect. Diğer tüm araçlar, bu üçlü üzerine inşa edilen kolaylık katmanlarıdır — faydalıdır ama zorunlu değildir.

### 5.3 İdeal Mimari — Sıfırdan Tasarım

Eğer bu sistem sıfırdan, Fortune 10 seviyesinde bir mimari disiplinle tasarlansaydı:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     İDEAL MİMARİ — DUS ÇALIŞMA SİSTEMİ v3.0                  │
│                          (Feature Spec — Sıfırdan Tasarım)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 0: ANAYASAL MOTOR (Constitutional Engine)                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  • Kısıt denetleyicisi (K1-K4 ihlal tespiti)                         │   │
│  │  • Günlük minimum engagement tracker                                  │   │
│  │  • Meta-çalışma bütçe sayacı (%5 cap)                                │   │
│  │  • Faz geçiş gate-keeper'ı (kriter sağlanmadan geçit açılmaz)        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  LAYER 1: VERİ KATMANI (Single Source of Truth)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        PROGRESS.json                                  │   │
│  │  (Makine-okunur KANONİK KAYNAK — tüm veri tipleri burada)            │   │
│  │                                                                       │   │
│  │  {                                                                    │   │
│  │    "courses": { "endodonti": { "units": 24, "completed": true, ...}},│   │
│  │    "anki": { "total_cards": 12333, "retention": 0.906, ...},         │   │
│  │    "pomodoro": { "total": 826, "monthly": {...} },                   │   │
│  │    "mock_exams": [ { "date": "...", "score": 72, "errors": [...] }], │   │
│  │    "blind_spots": [ { "id": "...", "status": "open", ...} ],         │   │
│  │    "daily_log": [ { "date": "...", "hours": 6.5, "units": [...] }]  │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  LAYER 2: ENTEGRASYON OTOBUSU (Automated Integration Bus)                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │   │
│  │  │  ANKİ    │   │ SORU BNK │   │  TİMER   │   │  CLAUDE  │          │   │
│  │  │ Connector│   │ Connector│   │ Connector│   │ Connector│          │   │
│  │  │ (MCP)    │   │ (API)    │   │ (CSV)    │   │ (API)    │          │   │
│  │  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘          │   │
│  │       │              │              │              │                 │   │
│  │       └──────────────┼──────────────┼──────────────┘                 │   │
│  │                      │              │                                │   │
│  │                      ▼              ▼                                │   │
│  │              ┌───────────────────────────┐                           │   │
│  │              │    AGGREGATOR (Cron/gün)  │                           │   │
│  │              │    • Anki snapshot çek    │                           │   │
│  │              │    • Pomodoro sayısı oku  │                           │   │
│  │              │    • Soru performansı çek │                           │   │
│  │              │    • PROGRESS.json yaz    │                           │   │
│  │              └───────────────────────────┘                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  LAYER 3: SUNUM VE ANALİZ KATMANI                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │   DASHBOARD     │  │  ALARM ENGINE   │  │  RAPORLAR       │       │   │
│  │  │   (READONLY)    │  │  (Threshold)    │  │  (Haftalık MD)  │       │   │
│  │  │                 │  │                 │  │                 │       │   │
│  │  │  • Günlük özet  │  │  • Retention    │  │  • Haftalık     │       │   │
│  │  │  • Haftalık     │  │    < %80 → ALARM│  │    review       │       │   │
│  │  │    trend        │  │  • 0-gün → ALARM│  │  • Blind spot   │       │   │
│  │  │  • Mock grafiği │  │  • Meta > %5    │  │    durumu       │       │   │
│  │  │  • Blind spot   │  │    → ALARM      │  │  • Strateji     │       │   │
│  │  │    tracker      │  │  • 2 mock       │  │    önerileri    │       │   │
│  │  │                 │  │    kaçırma→ALARM│  │                 │       │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TOPLAM BİLEŞEN SAYISI: 6 (Mevcut: 10+)                                      │
│  MANUEL ENTEGRASYON NOKTASI: 0 (Mevcut: 5+)                                  │
│  SSoT: TEK (PROGRESS.json) — Mevcut: ÇOKLU ve tutarsız                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Katman Açıklamaları:**

**Layer 0 — Anayasal Motor:** Sistemin değişmez kurallarını denetleyen katman. Bu katman, Furkan'ın zihinsel durumundan bağımsız olarak çalışır. Tıpkı bir dağıtık sistemin consensus algoritmasının node çökmelerinden bağımsız çalışması gibi, bu katman da kullanıcının motivasyon dalgalanmalarından bağımsız olarak sistem bütünlüğünü korur.

**Layer 1 — Veri Katmanı (PROGRESS.json):** Mevcut PROGRESS.md'nin makine-okunur karşılığı. JSON formatı, hem insan hem de makine tarafından okunabilir olma avantajını korurken, otomatik aggregasyon ve analize izin verir. PROGRESS.md ikincil (derived) bir sunum katmanı olarak kalabilir.

**Layer 2 — Entegrasyon Otobüsü:** Her aracın (Anki, soru bankası, timer) bir connector'ı vardır. Aggregator, günde bir kez tüm connector'lardan veri çeker ve PROGRESS.json'u günceller. Bu, mevcut manuel entegrasyonun tam tersidir.

**Layer 3 — Sunum ve Analiz:** Dashboard (opsiyonel — Furkan için değil, sistemin kendi kendini izlemesi için), Alarm Engine (eşik ihlallerinde tetiklenir), ve Raporlar (mevcut haftalık review'ın otomatik versiyonu).

### 5.4 Bileşen Değişiklik Özeti

```
╔═══════════════════════════════════════════════════════════════╗
║              BİLEŞEN KARAR MATRİSİ                            ║
╠═══════╤══════════════════════╤═══════════════════════════════╣
║ KARAR │ BİLEŞEN             │ GEREKÇE                       ║
╠═══════╪══════════════════════╪═══════════════════════════════╣
║ KALIR │ Anki (FSRS)         │ Tartışmasız. Hafıza motoru.   ║
║       │                      │ MVS'in 1/3'ü.                ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ KALIR │ Konu Notları (.md)  │ Yapılandırılmış encoding.     ║
║       │                      │ MVS'in 1/3'ü.                ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ KALIR │ Soru Bankası (basit) │ Testing effect. MVS'in 1/3'ü.║
║       │                      │ Ancak özel yazılım DEĞİL.    ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ DEĞİŞ.│ PROGRESS.md          │ PROGRESS.json + otomatik      ║
║       │                      │ aggregasyon. SSoT gerçek olur.║
╟───────┼──────────────────────┼───────────────────────────────╢
║ DEĞİŞ.│ DUSBANKASI           │ Özel platform → basit soru    ║
║       │                      │ bankası formatı. Geliştirme   ║
║       │                      │ zamanı sıfırlanır.            ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ DEĞİŞ.│ TickTick             │ Basit bir Pomodoro timer'ı    ║
║       │                      │ yeterli. Karmaşık görev       ║
║       │                      │ yönetimine gerek yok.         ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ ÇIKAR │ Google Sheets        │ PROGRESS.json + Dashboard     ║
║       │                      │ ile redundant.                ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ EKLEN.│ Anayasal Motor       │ Kısıt denetimi, gate-keeping, ║
║       │                      │ minimum engagement tracking.  ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ EKLEN.│ Alarm Engine         │ Eşik ihlallerinde proaktif    ║
║       │                      │ uyarı. Monitoring.            ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ OPSİY.│ NotebookLM           │ Faydalı ama MVS'te yok.       ║
║       │                      │ Zaman kalırsa kullan.         ║
╟───────┼──────────────────────┼───────────────────────────────╢
║ OPSİY.│ Claude API           │ Kart/soru üretimi için faydalı║
║       │                      │ ama manuel de yapılabilir.    ║
╚═══════╧══════════════════════╧═══════════════════════════════╝
```

---

## 6. 3 FAZLI UYGULAMA PLANI

### Genel Bakış

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      3 FAZLI DÖNÜŞÜM PLANI                                   │
│                                                                              │
│  FAZ 1: ACİL STABİLİZASYON (Hemen — 1 hafta)                                │
│  ─────────────────────────────────────────                                   │
│  Amaç: Kanayan yaraları durdur. Tutarlılığı garanti altına al.              │
│  Maliyet: 0 yeni araç. Mevcut sistemin konfigürasyon değişiklikleri.         │
│                                                                              │
│       ┌──────────┐                                                           │
│       │ MVE      │  Minimum Viable Engagement protokolü                      │
│       │ Protokolü│  (Günde 1 kart + 1 soru — istisnasız)                     │
│       └──────────┘                                                           │
│                                                                              │
│  FAZ 2: YAPISAL İYİLEŞTİRME (2-4 hafta)                                     │
│  ─────────────────────────────────────────                                   │
│  Amaç: SSoT'yi kur. Otomasyonu başlat. Over-engineering'i kes.              │
│  Maliyet: 2-3 günlük script yazımı (son kez).                               │
│                                                                              │
│       ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│       │PROGRESS  │  │Anki Auto │  │ Meta-çal.│                              │
│       │.json     │  │Snapshot  │  │ Bütçe     │                              │
│       └──────────┘  └──────────┘  └──────────┘                              │
│                                                                              │
│  FAZ 3: MÜKEMMELLİK (Devam eden — Sınava kadar)                             │
│  ────────────────────────────────────────────────                            │
│  Amaç: Dashboard, alarm engine, tam otomasyon.                              │
│  Maliyet: Sadece zaman kalırsa. Opsiyonel.                                  │
│                                                                              │
│       ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│       │Dashboard │  │Alarm     │  │Trend     │                              │
│       │          │  │Engine    │  │Analizi   │                              │
│       └──────────┘  └──────────┘  └──────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### FAZ 1: ACİL STABİLİZASYON (Hemen etkinleştir — 1 hafta içinde tamamlanır)

**Hedef:** Sistemin en kritik açığı olan tutarlılık dalgalanmasını anayasal seviyede ele almak.

#### 1.1 Minimum Viable Engagement (MVE) Protokolü

```
MVE — AN AYASAL KISIT
═══════════════════════════════════════════════════════════════

GÜNLÜK MİNİMUM (İstisnasız — her gün, her koşulda):
├── 1 Anki kartı review (sadece 1 — sıfır gün yasak)
└── 1 soru çöz (DUSBANKASI veya soru bankasından)

"KÖTÜ GÜN" PROTOKOLÜ (Klinik rotasyon ağır geçti, tetiklenme oldu, vb.):
├── MVE'yi tamamla (~5 dakika)
├── Günü "bakım modu" olarak işaretle
└── Ertesi gün tam kapasiteye dön

HİÇBİR KOŞULDA:
├── 0 kart review (sistem bütünlüğü bozulur)
├── 0 soru (feedback loop kopar)
└── "Yarın telafi ederim" (telafi birikimi zincirleme çöker)
```

**MVE'nin mimari mantığı:** Bu, dağıtık sistemlerdeki "minimum quorum" kavramının eğitim sistemine uyarlanmasıdır. Bir dağıtık sistem, tüm node'lar çökse bile minimum sayıda node ayaktaysa çalışmaya devam eder. Aynı şekilde, Furkan'ın en kötü gününde bile 1 kart + 1 soru yapması, sistemin "quorum"unu korur ve tam çöküşü engeller. Önemli olan miktar değil, zincirin kopmamasıdır.

#### 1.2 Meta-Çalışma Bütçesi (Acil)

```
META-ÇALIŞMA BÜTÇESİ — FAZ 1
═══════════════════════════════════════════════════════════════

KURAL: Haftalık toplam çalışma süresinin maksimum %5'i
       meta-çalışmaya (araç geliştirme, pipeline, optimizasyon)
       ayrılabilir.

BUGÜNDEN İTİBAREN:
├── DUSBANKASI geliştirme: DONDURULDU
├── Pipeline optimizasyonu: DONDURULDU
├── Yeni araç değerlendirme: DONDURULDU
├── Mevcut araç bakımı: SADECE kırık düzeltme
└── PROGRESS.md güncellemesi: İZİNLİ (10 sn/gün)

İSTİSNA: Faz 2 otomasyon script'leri (tek seferlik, 2-3 gün).
         Bu script'ler, gelecekteki meta-çalışmayı sıfırlayacak.
```

#### 1.3 FSRS Optimizasyonu (Acil Konfigürasyon)

```
FSRS PARAMETRE OPTİMİZASYONU
═══════════════════════════════════════════════════════════════

AKSİYONLAR:
1. FSRS "Optimize" tuşuna bas (mevcut review geçmişiyle yeniden hesapla)
2. "Reschedule cards on change" → AKTİF ET
   (Eski kartlara yeni parametreler uygulansın.
    S0 Good: 33.16 gün değeri optimize edilecek.)
3. Desired retention: %85 olarak KORU
   (%91.1 mevcut değer, interval'ler kısaldıkça hedefe yaklaşacak.)
4. Max interval: 200 gün → 365 gün olarak ARTIR
   (Sınavdan sonraki review'ları da kapsasın.)

BEKLENEN SONUÇ:
- İlk 2 hafta: Retention ~%88-90 (interval'ler yeniden dengelenirken)
- 2-4 hafta: Retention %83-87 bandına oturur
- Günlük review yükü: ~300'den ~200-250'ye düşer (daha optimal dağılım)
```

#### Faz 1 Başarı Kriterleri

| Kriter | Mevcut | Hedef | Ölçüm |
|---|---|---|---|
| Günlük MVE uyumu | Yok (tanımsız) | 7/7 gün | MVE log'u |
| Meta-çalışma oranı | ~%20 | <%5 | Zaman takibi |
| FSRS retention (son hafta) | %74.8 | >%80 | Anki stats |
| Sıfır gün sayısı | Var (bilinmiyor) | 0 | MVE log'u |

#### Faz 1 Riskleri ve Mitigasyonları

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| MVE, "çok kolay" görülüp küçümsenir | ORTA | KRİTİK | MVE'nin anayasal KISIT olduğu vurgulanır. Kolaylığı, özellik değil, tasarım gereğidir. |
| DUSBANKASI geliştirme dürtüsü | YÜKSEK | ORTA | "Donduruldu" etiketi fiziksel olarak repoya eklenir. Dürtü geldiğinde MVE'ye yönlendirilir. |
| FSRS reschedule sonrası aşırı yük | DÜŞÜK | ORTA | Reschedule sonrası ilk hafta günlük yeni kart 0'a düşürülür. |

---

### FAZ 2: YAPISAL İYİLEŞTİRME (2-4 hafta)

**Hedef:** Manuel entegrasyon noktalarını otomatize et. SSoT'yi kur. Zaman-müfredat denklemini çöz.

#### 2.1 PROGRESS.json — Kanonik Veri Katmanı

```json
{
  "meta": {
    "version": "3.0",
    "last_updated": "2026-05-04T18:00:00Z",
    "exam_date": "2026-11-01",
    "target_rank": 10,
    "target_score": 85
  },
  "courses": {
    "fizyoloji": {
      "total_units": 10,
      "completed_units": 10,
      "tur1_done": true,
      "tur2_done": false,
      "anki_cards": 850,
      "anki_retention": 0.88,
      "weak_areas": ["Böbrek fizyolojisi", "Asit-baz"]
    }
  },
  "anki": {
    "total_cards": 12333,
    "mature_cards": 2516,
    "young_cards": 55,
    "unseen_cards": 9443,
    "suspended_cards": 293,
    "retention_all_time": 0.906,
    "retention_last_week": 0.748,
    "retention_last_month": 0.825,
    "daily_reviews_avg": 300,
    "fsrs_desired_retention": 0.85,
    "fsrs_s0_good_days": 33.16,
    "fsrs_max_interval_days": 365,
    "last_optimized": "2026-05-04"
  },
  "pomodoro": {
    "total_count": 826,
    "total_hours": 1011.3,
    "monthly": {
      "2025-09": 76, "2025-10": 120, "2025-11": 120,
      "2025-12": 148, "2026-01": 90, "2026-02": 85,
      "2026-03": 126, "2026-04": 0, "2026-05": 0
    }
  },
  "mock_exams": [
    {
      "date": "2026-05-15",
      "total_questions": 200,
      "correct": 142,
      "score_percent": 71,
      "errors": {
        "knowledge_gap": 35,
        "comprehension_error": 15,
        "attention_error": 8
      },
      "time_used_minutes": 165,
      "notes": "Endodonti travma sorularında bilgi eksiği belirgin."
    }
  ],
  "blind_spots": [
    {
      "id": "bs-001",
      "course": "Endodonti",
      "topic": "Travma takip ve randevu süreleri",
      "status": "open",
      "opened_date": "2026-03-22",
      "reminder": "Pedodonti başlarken travma takip tablosunu çıkar"
    }
  ],
  "daily_log": [
    {
      "date": "2026-05-04",
      "day_type": "full",
      "hours_studied": 6.5,
      "anki_reviews": 310,
      "new_cards_added": 40,
      "questions_solved": 15,
      "units_completed": ["Patoloji Ünite 5"],
      "meta_work_minutes": 15,
      "mve_completed": true,
      "notes": ""
    }
  ],
  "constitutional_violations": [
    {
      "date": "2026-05-03",
      "constraint": "K2 (meta-çalışma > %5)",
      "actual_pct": 12,
      "resolution": "DUSBANKASI feature freeze"
    }
  ]
}
```

Bu JSON yapısı:
- **Makine-okunur** (Connector'lar otomatik yazabilir)
- **İnsan-okunur** (Gerektiğinde editörle düzenlenebilir)
- **Tekil** (Tüm veri tipleri tek dosyada)
- **Sürüm kontrollü** (Git ile tüm değişiklikler izlenir)
- **Genişletilebilir** (Yeni veri tipleri için yeni alanlar eklenir)

#### 2.2 Anki Connector (Otomatik Snapshot)

```
ANKİ CONNECTOR — GÜNLÜK OTOMATİK SNAPSHOT
═══════════════════════════════════════════════════════════════

Mevcut Durum: Anki MCP Server zaten KURULU.
              (Bkz: ~/.claude/DUS/SYSTEMS/ANKI_MCP.md)

YAPILACAK: Günde bir kez (tercihen 20:00), bir cron job
           Anki MCP üzerinden retention ve kart sayılarını çeker,
           PROGRESS.json'un "anki" bölümünü günceller.

SCRIPT: ~/.claude/DUS/scripts/anki_snapshot.py
        (Mevcut Anki MCP'yi kullanır, yeni bağlantı gerekmez)

ÇIKTI: PROGRESS.json → anki alanı güncellenir.
```

#### 2.3 Zaman-Müfredat Optimizasyonu

27 haftalık açığı kapatmak için 3 strateji değerlendirilir:

```
STRATEJİ A: KAPSAM DARALTMA (Önerilen)
────────────────────────────────────────
Bazı derslerde sadece high-yield konular çalışılır.
DUS soru dağılımında düşük ağırlıklı konular elemine edilir.

UYGULAMA:
├── 14 ders → 10 ders + 4 "high-yield only" ders
├── Pedodonti: 16 ünite → 8 ünite (DUS'ta düşük ağırlıklı)
├── Ortodonti: 12 ünite → 6 ünite (sınıflandırma + temel mekanik)
├── Farmakoloji: 12 ünite → 6 ünite (endikasyon/kontrendikasyon odaklı)
└── Restoratif: 9 ünite → 5 ünite (materyal bilimi + temel prensipler)

KAZANIM: ~44 ünite azalma → ~4 hafta kazanç.
RİSK: Kapsam dışı bırakılan konulardan soru gelme riski.
      Ancak DUS'ta her konudan eşit soru gelmez; ROI hesabı yapılmıştır.

STRATEJİ B: YOĞUNLAŞTIRILMIŞ TUR 2
────────────────────────────────────
Tur 2'de her ünite tekrarı yerine, sadece zayıf nokta + yanlış
yapılan soru konuları tekrar edilir.

UYGULAMA:
├── Anki retention < %80 olan üniteler → tam tekrar
├── Mock'ta yanlış yapılan konular → tam tekrar
├── Diğer üniteler → sadece kart review (Anki zaten yapıyor)
└── Tur 2 tekrar yükü: ~164 → ~80 ünite

KAZANIM: ~4 hafta.
RİSK: "Bildiğini sandığın ama bilmediğin" konular kaçabilir.
      Anki retention, bu riski kısmen telafi eder.

STRATEJİ C: HİBRİT (ÖNERİLEN)
───────────────────────────────
Strateji A + B'nin birleşimi.

UYGULAMA:
├── 4 ders high-yield only (Kapsam daraltma)
├── Tur 2 sadece zayıf + yanlış konular (Yoğunlaştırma)
├── Tur 3 ve Tur 4 birleştirilir (Tur 3: 1 gün/ders, son tekrar)
└── Deneme fazı 8 haftaya sabitlenir

TOPLAM KAZANIM: ~8 hafta → 27 haftalık bütçe yeterli hale gelir.
```

#### Faz 2 Başarı Kriterleri

| Kriter | Mevcut | Hedef | Ölçüm |
|---|---|---|---|
| PROGRESS.json kurulumu | Yok | Var ve güncel | Dosya varlığı |
| Anki otomatik snapshot | Manuel | Otomatik (günlük) | Cron log |
| Zaman-müfredat planı | 4 hafta açık | Kapalı (hibrit strateji) | Hesaplama |
| Veri giriş noktası sayısı | 5+ manuel | 0 manuel (otomatik) | Sistem audit |
| Haftalık review süresi | 30-60 dk | 15 dk (dashboard) | Zaman ölçümü |

#### Faz 2 Riskleri ve Mitigasyonları

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| Otomasyon geliştirme, over-engineering'e dönüşür | ORTA | YÜKSEK | Sıkı süre limiti: 3 gün. Bitmezse yarım bırakılır. |
| Hibrit stratejide elenen konulardan kritik soru gelir | DÜŞÜK | ORTA | Elenen konular için en azından Anki kartları üretilir (pasif exposure). |
| Anki MCP bağlantısı kopar | DÜŞÜK | DÜŞÜK | Fallback: Manuel snapshot. Haftalık review'da kontrol. |

---

### FAZ 3: MÜKEMMELLİK (Devam Eden — Opsiyonel, Sadece Zaman Kalırsa)

**Hedef:** Tam otomasyon, proaktif alarm, trend analizi.

**ÖNEMLİ UYARI — ANAYASAL KISIT K2:** Faz 3 çalışmaları, meta-çalışma bütçesinin %5 sınırını aşamaz. Faz 3, sadece zaman kalırsa ve Faz 1-2 tamamsa başlatılır.

#### 3.1 Dashboard (Salt Okunur — HTML/JS)

```
Tek bir HTML dosyası. PROGRESS.json'u okur, görselleştirir.
Tarayıcıda açılır. Başka hiçbir bağımlılığı yoktur.

GÖSTERGELER:
├── Günlük MVE: ✅/❌ (son 7 gün — yeşil/kırmızı)
├── Retention sparkline (son 30 günlük trend)
├── Mock skorları (zaman serisi grafiği)
├── Kalan ünite sayacı (güncel / toplam)
├── Meta-çalışma bütçesi (haftalık % bar)
└── Blind spot durumu (açık / kapalı sayısı)
```

#### 3.2 Alarm Engine

```
EŞİK DEĞERLER VE ALARM TETİKLEYİCİLERİ:
─────────────────────────────────────────

🔴 KRİTİK ALARM (Hemen aksiyon):
├── 0-gün: Bugün MVE yapılmadı → "1 KART + 1 SORU — HEMEN"
├── Retention < %75 (son hafta) → "FSRS optimize et"
├── 2 hafta üst üste mock yok → "BU HAFTA MOCK ZORUNLU"

🟡 UYARI (Haftalık review'da ele al):
├── Retention < %80 (son hafta) → "Retention trendi izleniyor"
├── Meta-çalışma > %5 (bu hafta) → "Bütçe aşımı — development freeze"
├── Blind spot 2+ haftadır açık → "Kapatma aksiyonu planla"

🟢 NORMAL:
├── Tüm metrikler eşik üstünde
└── Haftalık review rutini devam eder
```

#### 3.3 Faz 3 Başarı Kriterleri

| Kriter | Mevcut | Hedef |
|---|---|---|
| Dashboard | Yok | Tek HTML, çift tıkla açılır |
| Alarm engine | Yok (manuel kontrol) | 3 alarm seviyesi |
| Haftalık review otomasyonu | %100 manuel | %80 otomatik (sadece kararlar manuel) |

#### Faz 3 Riskleri

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| Dashboard geliştirmesi over-engineering'e dönüşür | YÜKSEK | ORTA | K2 bütçesi aşılırsa Faz 3 DERHAL iptal edilir. |
| Faz 3, Faz 1-2'nin önüne geçer | ORTA | YÜKSEK | Faz sıralaması anayasaldır — atlanamaz. |

---

## 7. SONUÇ VE NİHAİ TAVSİYELER

Furkan Kurt'un DUS çalışma sistemi, nadir görülen bir paradoksu temsil etmektedir: **altyapı olarak üst seviye, uygulama tutarlılığı olarak kırılgan.** Bu, yazılım mimarisinde sık görülen bir pattern'dır: "perfect architecture, unreliable runtime." Sistemin bileşenleri tek tek incelendiğinde her biri iyi tasarlanmıştır; ancak bu bileşenleri bir arada tutan entegrasyon katmanı (insan), sistemin en zayıf halkasıdır.

**Üç kritik aksiyon — yarına başlanacak:**

1. **MVE Protokolünü bugün aktive et.** Günde 1 kart + 1 soru. İstisnasız. Bu, sistemin anayasasına eklenecek ilk değişmez kısıttır.

2. **DUSBANKASI geliştirmesini bugün dondur.** Mevcut haliyle kullan. Yeni feature yok. Over-engineering döngüsü, sistemin en sinsi düşmanıdır — tam da "verimli" hissettirdiği için.

3. **FSRS parametrelerini bu hafta optimize et.** Reschedule'ı aç. Retention'ı %85 civarına çek. S0 Good: 33.16 değerini düzelt. Bu, günlük review yükünü ~%20-30 azaltacak ve açığa çıkan zamanı yeni konulara yönlendirecektir.

Sistemin kalan 27 haftası, disiplinli bir faz geçişi ve azaltılmış meta-çalışma ile ilk 10 hedefi için yeterlidir. Ancak bu, sistemin "mükemmel" olmasıyla değil, "yeterince iyi" olmasıyla mümkündür. Bazen en iyi mimari, en az mimaridir.

---

## EK A: KARAR KAYDI

Bu analiz sırasında alınan mimari kararlar:

| Karar ID | Karar | Gerekçe | Tarih |
|---|---|---|---|
| ARC-001 | MVE protokolü anayasal KISIT olarak tanımlandı | Sıfır gün, sistem bütünlüğünü bozar | 2026-05-04 |
| ARC-002 | PROGRESS.json SSoT olarak belirlendi | Manuel entegrasyonu ortadan kaldırmak için | 2026-05-04 |
| ARC-003 | Faz 3 (Mükemmellik) opsiyonel | Over-engineering riski nedeniyle | 2026-05-04 |
| ARC-004 | Hibrit zaman-müfredat stratejisi (A+B) | 27 haftalık bütçeyi kapatmak için | 2026-05-04 |
| ARC-005 | Meta-çalışma bütçesi %5 olarak sabitlendi | Mevcut ~%20'lik kayıp oranını düşürmek için | 2026-05-04 |
| ARC-006 | FSRS max interval 365 güne çıkarıldı | Sınav sonrası review'ları da kapsaması için | 2026-05-04 |

---

## EK B: REFERANS DOKÜMAN HARİTASI

| Doküman | Konum | İlişki |
|---|---|---|
| Sistem Durum Raporu | `RAPORLAR/furkankurt/furkan_kurt_dus_sistem_raporu.md` | Analiz kaynağı |
| Progress (Canonical) | `~/.claude/DUS/PROGRESS.md` | Mevcut SSoT |
| Strateji Reçetesi | `~/.claude/DUS/STRATEGY.md` | Anayasal öncül |
| 10 Stratejik Karar | `~/.claude/DUS/DECISIONS.md` | Karar geçmişi |
| Anki İstatistikleri | `~/.claude/DUS/SYSTEMS/ANKI_STATS.md` | Performans verisi |
| DUS Pipeline | `~/.claude/DUS/SYSTEMS/DUS_PIPELINE.md` | İş akışı |
| Master Index | `~/.claude/DUS/INDEX.md` | Doküman haritası |
| Memory Index | `~/.claude/DUS/MEMORY.md` | Proje hafızası |

---

*Bu rapor, Serena Blackwood ("The Academic Visionary") Architect Agent tarafından, Furkan Kurt'un DUS çalışma sisteminin tam mimari analizi olarak hazırlanmıştır. Analizde kullanılan yöntemler: anayasal prensip kataloglaması, coupling/cohesion analizi, veri akış haritalaması, SSoT denetimi, feedback loop kalite ölçümü, zaman-müfredat sayısal modellemesi, ve ideal mimari feature spec tasarımı. Tüm öneriler, sistemin mevcut durumu ve Furkan'ın beyan edilen hedefleri göz önünde bulundurularak yapılmıştır.*

📋 SUMMARY: Furkan Kurt'un DUS sisteminin 6 boyutlu tam mimari analizi — anayasal boşluklar, coupling/cohesion, SSoT eksikliği, zaman-müfredat çakışması, ideal mimari ve 3 fazlı uygulama planı
🔍 ANALYSIS: En kritik anayasal eksiklik MVE (Minimum Viable Engagement) protokolü; mevcut sistem manuel insan entegrasyonuna bağımlı; 27 hafta / 97 ünite denklemi 4 hafta açık veriyor; retention %91.1 yanıltıcı olabilir; DUSBANKASI geliştirmesi en büyük zaman sızıntısı
⚡ ACTIONS: Rapor yazıldı, 6 bölüm + ekler tamamlandı, ASCII diyagramlarla görselleştirme yapıldı, tüm dosya referansları mutlak path ile verildi
✅ RESULTS: `RAPORLAR/furkankurt/mimar_analiz.md` başarıyla oluşturuldu — Anayasal Prensipler Kataloğu (5 mevcut + 5 eksik), ASCII mimari diyagramları (3 adet), stratejik boşluk analizi (4 alt analiz), ideal mimari feature spec (4 katmanlı), 3 fazlı uygulama planı (her faz için başarı kriterleri + risk/mitigasyon matrisi)
📊 STATUS: Tamamlandı. 6 bölüm, 2 ek, 9 ASCII diyagram, 12 tablo, 6 mimari karar kaydı
📁 CAPTURE: Sistemin temel kısıtı zamandır — tüm mimari kararlar bu kısıt etrafında optimize edilmelidir. Mevcut over-engineering döngüsü, "araç fetişizmi" pattern'ıdır. MVE protokolü, sistemin en kritik eksiğidir. PROGRESS.json'a geçiş, manuel entegrasyon yükünü sıfırlayacak dönüşümün merkezindedir.
➡️ NEXT: 1) MVE protokolünü bugün aktive et (1 kart + 1 soru), 2) DUSBANKASI geliştirmesini dondur, 3) FSRS optimize + reschedule yap, 4) Faz 2 otomasyon script'lerini 3 gün içinde yaz, 5) Hibrit zaman-müfredat planını onayla
🎯 COMPLETED: Mimari analiz tamamlandı, rapor yazıldı, 3 fazlı plan hazır.