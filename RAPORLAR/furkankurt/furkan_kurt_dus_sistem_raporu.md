# FURKAN KURT — DUS ÇALIŞMA SİSTEMİ: OBJEKTİF DURUM RAPORU

**Rapor Tarihi:** Mayıs 2026  
**Hedef:** Bu raporun birincil kullanım amacı, bir LLM ajanının Furkan Kurt'un DUS hazırlık sistemini analiz edebilmesi için gereken tam bağlamı sağlamaktır. Tüm veriler gözlemlenmiş örüntüler ve beyan edilen bilgilerden derlenerek tarafsız biçimde sunulmuştur.

---

## 1. GENEL BAĞLAM VE HEDEF

### 1.1 Kimlik ve Akademik Pozisyon

Furkan Kurt, İstanbul Üniversitesi Diş Hekimliği Fakültesi 5. sınıf (intern) öğrencisidir. 24 yaşındadır. Mezuniyet aşamasında olup aynı anda klinik rotasyon yükümlülüklerini, bitirme tezini ve DUS hazırlığını paralel yürütmektedir.

### 1.2 Sınav Hedefi

- **Sınav:** DUS (Diş Hekimliğinde Uzmanlık Sınavı)
- **Tarih:** 1 Kasım 2026
- **Aday havuzu:** ~8.000 kişi
- **Hedef sıralama:** İlk 10 (üst %0.125)
- **Hedef bölüm:** Ankara Üniversitesi — Ağız, Diş ve Çene Cerrahisi
- **Uzun vadeli vizyon:** Oral cerrahi + implantoloji + protetik entegrasyon içeren multidisipliner özel klinik kuruculuğu

### 1.3 Zaman Çerçevesi

- **Başlangıç tarihi:** 19 Mart 2026
- **Kalan süre (Mayıs 2026 itibarıyla):** ~27 hafta
- **Aktif faz:** Faz 2 — Tur 2 (Spaced Repetition fazı)

---

## 2. ÇALIŞMA TAKVİMİ VE GÜNLÜK YAPI

### 2.1 Zaman Bloklama Mimarisi

Furkan, günlük yapısını iki ana bilişsel bloka ayırmaktadır:

| Blok | Saat Aralığı | İçerik | Biliş Yükü |
|---|---|---|---|
| Sabah | 07:00–11:00 | Klinik rotasyon | Yüksek (pratik) |
| Öğleden Sonra | 12:00–20:00 | DUS çalışma blokları | Yüksek (aktif öğrenme + review) |
| Akşam | 21:00+ | Kaçınılan dilim | Kaçınılır |

Peak çalışma saatleri olarak 07:00–11:00 derin analiz ve aktif öğrenme; 12:00–20:00 tekrar ve aktif geri çağırma işlevleri üstlenmektedir.

### 2.2 Pomodoro Yapısı

Birincil teknik: **Pomodoro 90/20** — 90 dakika kesintisiz çalışma, 20 dakika dinlenme. Bu yapı standart 25/5 Pomodoro'nun ötesinde, yüksek kognitif derinlik gerektiren konular için tercih edilmektedir.

### 2.3 Tarihsel Çalışma Verisi

| Ay | Toplam Saat |
|---|---|
| Eylül 2025 | ~76 saat |
| Ekim 2025 | ~120 saat |
| Kasım 2025 | ~120 saat |
| Aralık 2025 | ~148 saat |
| Ocak 2026 | ~90 saat |
| Şubat 2026 | ~85 saat |
| Mart 2026 | ~126 saat (zirve) |

**Toplam:** 826 Pomodoro / 1.011+ saat (Eylül 2025 — Mart 2026)

**Gözlemlenen örüntü:** Tutarlılık oranı tarihsel olarak %32–62 aralığında seyretmiş; Aralık 2025 ve Mart 2026 zirve noktaları oluştururken Ocak–Şubat döneminde belirgin düşüş yaşanmıştır. Başlangıç momentumu kritik değişken olarak tanımlanmıştır.

---

## 3. MÜFREDATPRİORİTİZASYONU VE KONU SIRASI

### 3.1 Tamamlanan Dersler (Tur 1)

| Ders | Ünite Sayısı | Durum |
|---|---|---|
| Fizyoloji | 10/10 | Tamamlandı |
| Protez | 20/20 | Tamamlandı |
| Periodontoloji | 12/12 | Tamamlandı |
| Histoloji | 17/17 | Tamamlandı |
| Endodonti | 24/24 | Tamamlandı |

### 3.2 Aktif Ders

- **Patoloji:** 4/11 ünite (devam ediyor)

### 3.3 Planlanan Konu Sırası

Radyoloji → Cerrahi-Anatomi → Biyokimya → Ortodonti → Restoratif → Pedodonti → Mikrobiyoloji → Farmakoloji

Bu sıralama, DUS'ta soru yoğunluğu ve branş ROI analizi temel alınarak belirlenmiştir. 480 soruyu kapsayan dört dönem analizi yapılarak her branşın soru miktarı, pratik kazanım ve çalışma süresi kesiştirmesine dayalı öncelik listesi oluşturulmuştur.

---

## 4. ANKİ SİSTEMİ VE SPACED REPETITION YAPISI

### 4.1 Temel Metrikler

| Metrik | Değer |
|---|---|
| Toplam kart sayısı | 10.851 |
| Mevcut retention oranı | %91.1 |
| FSRS hedef hatırlanabilirlik | %89 |
| Günlük review hacmi | ~300 kart/gün |

### 4.2 Algoritma: FSRS

Furkan, standart SM-2 yerine **FSRS (Free Spaced Repetition Scheduler)** algoritmasını kullanmaktadır. FSRS parametreleri:

- **Hedef retention:** %85 (konfigürasyona göre değişmiş; mevcut fiili %91.1)
- **Learning steps:** Optimize edilmiş; kısa aralıklarla çok adımlı geçiş
- **Leech threshold:** Tanımlanmış eşik değeri
- **Max interval:** Sınırlandırılmış
- **Önemli geçmiş:** Kartların graduation'ı erken tamamlayan bir scheduling bug tespit edilmiş ve çözülmüştür

### 4.3 Kart Tipolojisi

İki birincil kart formatı kullanılmaktadır:

**Basic Kart:** Soru–Cevap yapısı. Kavramsal tanımlama, mekanizma açıklaması, klinik senaryo eşleştirmesi için tercih edilir.

**Cloze Kart:** Boşluk doldurma. Terminoloji, sınıflandırma, sayısal eşik değerleri, spesifik marker'lar için tercih edilir.

Dual-deck stratejisi uygulanmaktadır: Basic ve Cloze kartlar ayrı decklerde tutulmakta, ancak FSRS ile koordineli biçimde yönetilmektedir.

### 4.4 Kart Üretim İlkeleri

Furkan'ın Anki kart üretimi için tanımladığı kurallar (PROMPT CLOZE v2.1, PROMPT v7 ve aktif versiyonlara dayalı):

- **Atomik yapı:** Her kart tek bir bilgi parçası içerir — bilgi parçalanmaz
- **Semantik kaçak önleme:** Kart, cevabı ima eden ipuçları barındıramaz
- **Mekanizma bağlantısı:** İzole fact yerine nedensellik zinciri içeren kart tercih edilir
- **Klinik marker kapatma:** Her kart DUS sınav pattern veya klinik yansıma ile biter
- **Paraphrase yasağı:** Transformation (dönüştürücü çıktı) esastır, pasif bilgi kopyası değil

---

## 5. ÖĞRENME METODOLOJİSİ

### 5.1 Top-Down Mimari

Furkan'ın bilgi işleme tarzının belirleyici özelliği: **root-cause önce, detay sonra** hiyerarşisidir. Bir konuya başlamadan önce şu soruların yanıtlanması zorunludur: "Bu mekanizmanın temel nedeni nedir?" ve "Bu süreç bir sonraki adımı nasıl tetikler?"

Bu yapı olmadan bilgi işleme gerçekleşmez; ezber direnci tanımlanmıştır. Mekanizma kurulduğu anda motivasyon ve kavrama hızı otomatik olarak geri döner.

### 5.2 Kaskad Analizi

Bilgi izole olgular olarak değil, birbiri tetikleyen ardışık reaksiyonlar zinciri olarak işlenir. Örnek: "Periodontitis'te nötrofil fonksiyon bozukluğu → proteaz salınımı → bağ dokusu yıkımı → alveolar kemik kaybı" zinciri, her halka nedensellik ile bağlanmış biçimde kurulur.

### 5.3 Aktif Geri Çağırma ve Feynman

Pasif okuma reddedilmektedir. Birincil yöntemler:

- Aktif recall (anki kartları ve soru bankası)
- Feynman tekniği: kavramı sıfır referans ile yeniden açıklama
- Hata analizi: yanlış yanıtlanan sorularda mekanizma geri izlemesi

### 5.4 Araç Ekosistemi

| Araç | Fonksiyon |
|---|---|
| Anki (FSRS) | Uzun vadeli hafıza motoru, ~300 kart/gün review |
| TickTick | Zaman bloklama, günlük görev yönetimi |
| Google Sheets | Günlük çalışma takibi, performans grafikleri |
| NotebookLM | DUS müfredatı kaynaklarıyla yüklenmiş kavram netleştirme |
| Markmap | Python script ile otomatik zihin haritası üretimi |
| DUSBANKASI (özel) | Supabase + Vite/React/TypeScript + Python pipeline ile inşa edilmiş AI destekli soru bankası |
| Claude API | Kart üretimi, soru üretimi, klinik açıklama |
| Gemini | Ek AI katmanı |

### 5.5 DUSBANKASI Sistemi

Furkan'ın kendi geliştirdiği özel platform:

- **Backend:** Supabase (PostgreSQL + pgvector)
- **Frontend:** Vite / React / TypeScript
- **Pipeline:** Python + NotebookLM entegrasyonu
- **Özellikler:** Retroactive Expansion Mode (kavram parmak izi ile), semantik deduplication, RAG-tabanlı açıklama erişimi, zayıf nokta kümeleme
- **Vektör katmanı:** pgvector (birincil) + Pinecone (değerlendirilen ek katman)
- **LLM:** Anthropic Claude API

---

## 6. SORU BANKASI VE SINAV HAZIRLIĞI

### 6.1 Tarihsel Soru Analizi

480 DUS sorusu (dört dönem) analiz edilmiştir. Çıktılar:

- Branş bazında ROI önceliği (soru yoğunluğu × çalışma süresi ÷ zorluk)
- Soru mühendisliği analizi (hangi soru tipi hangi mekanizma katmanını hedefler)
- Master prompt sistemi (V2 Final): DUS formatında soru üretimi için

### 6.2 Quiz Uygulamaları

React tabanlı DUS format quiz uygulamaları üretilmiştir. Bu uygulamalar doğrudan Anthropic Claude API çağrısı yapmakta, dinamik soru üretimi ile gerçek sınav simülasyonu sağlamaktadır.

### 6.3 Hedef Skor

DUS hedef skoru: **85+** (mutlak puan hedefi). Sıralama hedefi: ilk 10.

---

## 7. ZİHİNSEL YAPI VE PERFORMANSEKONOMİSİ

### 7.1 Güçlü Özellikler (Çalışma Sistemiyle Doğrudan İlişkili)

- Sistem kurma ve uzun vadeli mimari tasarlama kapasitesi çok yüksektir (9.2/10 zeka + sistem düşüncesi skoru)
- Mekanizma temelli öğrenme yapısı, bilginin transferini kolaylaştırır
- Öz farkındalık yüksektir; hata döngülerini tespit edebilir
- Zihinsel dayanıklılık (8.7/10): kriz sonrası recovery fonksiyonel

### 7.2 Yapısal Riskler (Gözlemlenmiş)

**Over-engineering döngüsü:** DUS çalışması yerine sistem geliştirmeye (DUSBANKASI, prompt mühendisliği, araç optimizasyonu) zaman harcama eğilimi. Bu döngü, görünürde verimli hissettirdiği için tespit edilmesi güçtür.

**Tutarlılık dalgalanması:** İş tutarlılığı tarihsel olarak %32–62 arasında seyretmiştir. Yüksek motivasyon dönemlerinde pik yapılmakta; düşük motivasyon dönemlerinde sistem tamamen devre dışı kalabilmektedir.

**Tetiklenme sonrası odak kaybı:** Dışsal bir tetikleyici (liyakatsizlik, saygısızlık, belirsizlik) sonrasında yeniden odaklanma için kayda değer süre gerekmektedir (2.3/10 tetiklenme sonrası odak skoru).

**Aşırı öz farkındalık spirali:** Kriz anlarında meta-kognitif analiz kendi başına bilişsel yük oluşturabilmekte, bu durum çalışmadan ziyade kendini gözlemleme döngüsüne dönüşebilmektedir.

**Sabırsızlık riski:** Uzun soluklu süreçlerde motivasyon düşüşü tanımlanmış bir tuzaktır (3.6/10 sabır skoru).

### 7.3 Stres Belirtileri ve Kriz Protokolü

**Stres belirtileri:** Sosyal izolasyon, dürtüsel harcamalar, sistemsel angaryaya girme, odak kaybı.

**Kriz protokolü (tetikleyici ifadeler):**
- "Çok fazla bilgi"
- "Paralize oldum"
- "Nereden başlasam"
- "Tetiklenmiş durumdayım"

Bu ifadeler tespit edildiğinde uygulanacak yanıt: tek direktif adım (opsiyonsuz) + sonraki operasyonel hedef. Motivasyonel dil, empati, tablo, liste — yasaklı.

**Recovery mekanizması:** 10 dakikalık analitik öz eleştiri. Üç bileşen: hata teşhisi + başarı tespiti + tekrar edilecek davranış.

---

## 8. ÇALIŞMA SİSTEMİNİN STRATEJİK TASARIMI

### 8.1 Monk Mode

Aktif sosyal kısıtlama dönemi. İlişkisel ve sosyal bağlılık minimize edilmiş; enerji DUS + klinik rotasyon + kişisel gelişim eksenine kanalize edilmiştir.

### 8.2 Haftalık Review Ritüeli

Haftalık performans gözden geçirme: Tamamlanan Pomodoro sayısı, Anki retention değişimi, gözden geçirilen kart sayısı, konu ilerleme durumu ve kriz dönemlerinin nedensellik analizi.

### 8.3 Faz Yapısı

**Faz 1 — Tur 1 (Tamamlandı):** Her konunun ilk kez mekanistik anlama düzeyine çıkarılması.

**Faz 2 — Tur 2 (Aktif):** Spaced repetition ile pekiştirme; zayıf nokta odaklı derinleştirme; DUSBANKASI üzerinden soru pratiği.

---

## 9. KALİBRASYON VE OBJEKTİF DEĞERLENDİRME

### 9.1 Sistemin Güçlü Yönleri

Furkan'ın kurduğu sistem, birbiriyle entegre birkaç katmandan oluşmaktadır: uzun vadeli hafıza için FSRS destekli Anki; aktif üretim için AI destekli soru bankası; mekanizma temelli öğrenme metodolojisi; sistematik konu önceliği. Bu bütünleşik yapı, ortalama DUS adayının çalışma altyapısının üzerindedir.

### 9.2 Sistemin Açıkları

**Tutarlılık — sistemin en kırılgan noktasıdır.** Altyapı güçlü; uygulama tutarlılığı tarihsel olarak dalgalıdır. İlk 10 hedefi, altyapının varlığına değil, altyapının tutarlı biçimde kullanımına bağlıdır.

**Konu sırası ve zaman hesabı:** 27 haftalık kalan süre içinde geri kalan konuların (Radyoloji, Cerrahi-Anatomi, Biyokimya, Ortodonti, Restoratif, Pedodonti, Mikrobiyoloji, Farmakoloji) birinci tur tamamlaması + ikinci tur pekiştirmesi + soru pratiği için süre sıkışıktır.

**Over-engineering riski:** DUSBANKASI geliştirme, araç optimizasyonu ve sistem tasarımı süreleri, doğrudan konu çalışma süresiyle rekabet etmektedir. Bu dengenin nesnel olarak izlenmesi kritiktir.

**Retention hedefi ile mevcut retention tutarsızlığı:** FSRS hedefi %85 olarak tanımlanmışken mevcut retention %91.1 seviyesindedir. Bu durum ya kartların kolaylık eşiğini aşmış olduğuna ya da interval yapısının henüz optimal olmadığına işaret edebilir.

### 9.3 Kritik Değişkenler

Sistemin başarıya ulaşması için aşağıdaki değişkenlerin yönetimi belirleyicidir:

1. Günlük çalışma tutarlılığının %70+ üzerinde tutulması (tarihsel ortalama: %32–62)
2. Over-engineering döngüsünün haftalık review ile tespit ve kırılması
3. Patoloji + kalan konuların zaman planına göre tamamlanması
4. Kriz dönemlerinin çalışma bloklarına yayılmaması; recovery süresinin minimize edilmesi

---

## 10. ÖZET: SİSTEM PROFİLİ

| Boyut | Durum |
|---|---|
| Altyapı kalitesi | Yüksek — çok katmanlı, AI entegre, mekanizma temelli |
| Anki hacmi | 10.851 kart, %91.1 retention, FSRS aktif |
| Konu tamamlama | 5 ders Tur 1 tamamlandı; Patoloji aktif; 8 ders bekliyor |
| Günlük çalışma | 6–7 saat hedef; 90/20 Pomodoro |
| Tarihsel tutarlılık | %32–62 — en kritik açık |
| Sınav tarihi | 1 Kasım 2026 (~27 hafta) |
| Hedef sıralama | İlk 10 / ~8.000 kişi |
| Birincil risk | Tutarlılık + over-engineering döngüsü |
| Birincil güç | Mekanizma temelli öğrenme + sistematik altyapı |

---

*Bu rapor, gözlemlenmiş davranış örüntüleri, beyan edilen sistem parametreleri ve belgelenmiş performans verisinden derlenerek LLM analizi için hazırlanmıştır. Tarafsız ve operasyonel biçimde sunulmuştur.*
