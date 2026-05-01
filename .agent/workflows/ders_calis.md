# 📖 Ders Çalışma Protokolü (DUS Mentörü)
> Son güncelleme: 2026-04-28 | v8.0 — Yerel Vektörleme Zorunluluğu: MCP `search-records` kesinlikle yasaklandı, tüm aramalar yerel E5 + `run_command` ile yapılır. Kısa/özet yanıt yasağı korundu.

> **⚠️ TALİMAT:** Bir konu anlatımı veya soru çözümü talebi geldiğinde bu protokol EKSİKSİZ uygulanmalıdır. YANIT ASLA KISA OLAMAZ.

---

## ⛔ MUTLAK YASAKLAR (Tüm Adımlardan Öncelikli)

1. **KISA YANIT YASAĞI:** Yanıtlar ASLA kısa, özetlenmiş veya sığ olamaz. Her yanıt, kaynaktan gelen bilginin TAMAMINI kapsamak zorundadır. Kısa yanıt vermek bu protokolün EN AĞIR İHLALİDİR.
2. **SIFIR ÖZET & SIFIR KISALTMA:** Kaynak verileri asla özetlenemez, kısaltılamaz veya "temsili" olarak sunulamaz. Kaynakta ne varsa tam metin olarak sunulmalıdır.
3. **BELİRSİZ İFADE YASAĞI:** "gibi", "vb.", "vs.", "bazı belirtiler", "çeşitli nedenler", "birçok faktör", "diğerleri" gibi kestirme, muğlak ve belirsiz ifadeler KESİNLİKLE YASAKLANMIŞTIR. Bulunan tüm varyantlar, tipler, belirtiler, nedenler ve faktörler tek tek, madde madde, eksiksiz olarak yazılmak zorundadır.
4. **SIFIR HALÜSINASYON:** Pinecone'dan gelmeyen, kaynakta yer almayan bilgiler üretilemez. Sorgulanmayan frekanslar için tahmini sayı verilemez. Emin olunmayan bilgi için "Bilmiyorum, doğrulayalım" denmelidir.
5. **MEKANİZMA ŞARTI:** Mekanizmasız (A → B → C zinciri olmadan) bilgi vermek yasaktır. Her süreç, en az 3 basamaklı bir nedensellik zinciriyle açıklanmalıdır.

---

## 🔴 PINECONE ARAMA YASAĞI — KRİTİK KURAL

> **Pinecone bulut embedding kotası (multilingual-e5-large, 5M token/ay) DOLMUŞTUR.**
> Aşağıdaki yöntemler kesinlikle YASAKLANMIŞTIR çünkü bulut embedding tetiklerler:
>
> - ❌ `mcp_pinecone-mcp-server_search-records` (MCP aracı — inputs.text parametresi Pinecone bulut embedding kullanır)
> - ❌ `mcp_pinecone-mcp-server_cascading-search` (MCP aracı — aynı nedenle)
> - ❌ `index.search(query={"inputs": {"text": "..."}})` (Python SDK — aynı nedenle)
>
> **ZORUNLU ALTERNATİF:** Tüm aramalar aşağıdaki yerel vektörleme akışı ile yapılır:
> 1. Sorguyu **yerel E5-Large** ile vektörle → `run_command` ile `search_engine.py` çalıştır
> 2. Veya doğrudan `index.query(vector=[...], top_k=15)` kullan (ham vektör gönderimi)
>
> **İZİN VERİLEN MCP ARAÇLARI:**
> - ✅ `mcp_pinecone-mcp-server_rerank-documents` (Reranker — bulut embedding KULLANMAZ)
> - ✅ `mcp_pinecone-mcp-server_describe-index-stats` (İstatistik — embedding KULLANMAZ)
> - ✅ `mcp_pinecone-mcp-server_upsert-records` (Kayıt yazma — yerel vektörle birlikte kullanılır)
> - ✅ `mcp_pinecone-mcp-server_list-indexes` (Listeleme — embedding KULLANMAZ)

---

## ── FAZ 1: VERİ TOPLAMA (S5 Pipeline — Yerel Vektörleme ZORUNLU) ────

### Adım 1: Yerel Vektörleme & Pinecone Ham Vektör Araması

**Uygulama yöntemi (İKİ SEÇENEKten biri ZORUNLU kullanılır):**

**Seçenek A — `scripts/search_engine.py` CLI Kullanımı (ZORUNLU):**
```bash
# Tek Namespace Arama (Varsayılan - Sadece myppdfs):
python scripts/search_engine.py "KONU_ADI" --index myppdfs --ns radyoloji --top_k 15 --top_n 5

# Çoklu Namespace (Paralel) Arama (Sadece myppdfs):
python scripts/search_engine.py "KONU_ADI" --index myppdfs --ns radyoloji patoloji --top_k 15 --top_n 5

# JSON Çıktısı (Ajanlar için):
python scripts/search_engine.py "KONU_ADI" --ns radyoloji --json
```

**Seçenek B — Scratch Script (Ortam değişkenleri yüklü değilse):**
```python
# .env'den API key oku → Yerel E5 ile vektörle → index.query(vector=...) → rerank
# Bkz: scratch/study_search_v2.py şablonu
```

**ADIM SIRASI:**
1. Kullanıcının konusunu al
2. Konuyu `get_local_embedder().embed_text(query, is_query=True)` ile vektörle (YEREL CPU/GPU)
3. `index.query(vector=vektör, namespace="radyoloji", top_k=15, include_metadata=True)` ile Pinecone'a ham vektör gönder
4. Çoklu namespace varsa paralel arama yap (asyncio.gather veya sıralı)
5. Dönen sonuçları `pc.inference.rerank(model="bge-reranker-v2-m3", ...)` ile sırala → `top_n=5`
6. Gelen 5 parçanın metinleri HİÇ kırpılmadan, özetlenmeden Faz 2'ye geçirilir

**Kısıtlama:** Konu anlatımı sürecinde sadece `myppdfs` indeksi taranır. Akademik güvenilirlik için ana kaynak PDF verileridir. `mybrain` indeksi sadece kullanıcı spesifik notlarını sorduğunda iş akışına dahil edilir.
  - Örnek disiplin eşleşmeleri (myppdfs içinde): cerrahi ↔ anatomi, patoloji ↔ radyoloji, farmakoloji ↔ mikrobiyoloji.

---

## ── FAZ 2: İÇERİK SENTEZİ VE SUNUMU ────────────────────────────

> **TEMEL KURAL:** Aşağıdaki üç bölüm HER yanıtta ZORUNLUDUR. LLM, bölüm içi alt başlık yapısını konunun doğasına göre ÖZGÜRCE belirler (hastalık, anatomik yapı, alet, materyal, kavram — her biri farklı şablonda sunulabilir). Ancak üç bölümün varlığı ve sırası DEĞİŞMEZDİR.

### ─── BÖLÜM 1: HIGH-YIELD 20/80 ÖZÜ ───

- Konunun DUS'ta en çok sorulan, en çok karıştırılan ve kesinlikle bilinmesi gereken **patognomonik** ve **ayırt edici** bilgileri MADDE MADDE sunulur.
- Bu bölüm, konunun "sınav günü aklında kalması gereken" çekirdek bilgilerinden oluşur.
- Kısa ve vurucu cümleler tercih edilir; ancak hiçbir kritik bilgi atlanmaz.

### ─── BÖLÜM 2: KAPSAMLI KONU ANLATIMI ───

> **🔴 BU BÖLÜM YANITI UZUN YAPAN ANA BÖLÜMDÜR. ASLA KISALTMA!**

- Reranker'dan gelen 5 parçanın bilgilerini **bütüncül, akıcı ve tutarlı** bir konu anlatımı olarak birleştir. Parçalar arasındaki tekrarlayan bilgiler doğal olarak eritilir, ancak HİÇBİR BİLGİ ATILMAZ.
- Alt başlık yapısı konunun doğasına göre LLM tarafından belirlenir. Örnekler (zorunlu değil, yol gösterici):
  - **Hastalık/Lezyon:** Etyoloji → Patogenez (A→B→C) → Klinik Bulgular → Histopatoloji → Radyolojik Görünüm → Tedavi → Prognoz
  - **Anatomik Yapı:** Lokalizasyon → Komşuluk İlişkileri → Vaskülarizasyon/İnnervasyon → Klinik Önem → Cerrahi Vaka Önemi
  - **Endodontik/Restoratif Alet:** Aletin Özellikleri → Çalışma Prensibi → Endikasyonlar → Diğer Aletlerle Kıyaslaması
  - **Farmakolojik Ajan:** Etki Mekanizması → Farmakokinetik → Endikasyonlar → Yan Etkiler → İlaç Etkileşimleri → Benzer Ajanlarla Kıyaslaması
  - **Kavram/Prensip:** Tanım → Temel Mekanizma → Klinik Uygulama Alanları → Sık Sorulan Yönleri

- **ZORUNLU: Karşılaştırma Tabloları ve DUS Tuzakları**
  - Her konu anlatımında, konuyla **eş hiyerarşideki** kavramlar arasında en az bir detaylı markdown karşılaştırma tablosu oluşturulmalıdır.
  - Tablo örnekleri:
    - Ameloblastoma çalışılıyorsa → ayırıcı tanıdaki diğer odontojenik tümörlerle kıyaslama tablosu
    - K-file çalışılıyorsa → H-file, Reamer, Spreader ile karşılaştırma tablosu
    - N. facialis çalışılıyorsa → diğer benzer kranial sinirlerle ayrım tablosu
    - Anot çalışılıyorsa → Katot ile karşılaştırma tablosu
    - Bir materyal çalışılıyorsa → aynı sınıftaki diğer materyallerle kıyaslama tablosu
  - Tabloya ek olarak, konu içinde **DUS tuzakları**, **sık karıştırılan noktalar** ve **ayırıcı tanı ipuçları** ayrı madde başlıkları altında açıkça belirtilmelidir.

### ─── BÖLÜM 3: 5 KLASİK DUS SORUSU ───

- Konu anlatımının sonunda, anlatılan konuyla ilgili **tam 5 adet** klasik, çıkmış-tarzı DUS sorusu üretilir.
- Her soru:
  - 5 şıklı (A-B-C-D-E) olacak.
  - Doğru cevap açıkça belirtilecek.
  - Doğru cevabın mekanistik gerekçesi detaylıca açıklanacak.
  - **Her bir yanlış şıkkın neden yanlış olduğu** tek tek, mekanizma düzeyinde açıklanacak (eliminasyon mantığı).

---

## ── FAZ 3: SORU ÇÖZÜMÜ MODU (Soru Geldiyse) ──────────────────

Kullanıcı bir soru getirdiğinde, Faz 2'nin üç bölümüne ek olarak şu analiz yapılır:

1. **Doğru Cevap Analizi:** Doğru cevabın neden doğru olduğunu mekanistik (A→B→C) düzeyinde açıkla.
2. **Yanlış Şık Eliminasyonu:** Her bir yanlış şıkkın neden yanlış olduğunu ayrı ayrı, detaylı mekanizmalarla açıkla. Hiçbir şık "zaten yanlış" diye geçiştirilemez.
3. **Çeldirici Analizi:** Sorunun hangi DUS tuzağını test ettiğini, hangi kavramın hangi kavramla karıştırılmasının amaçlandığını belirt.
4. **İlişkili Konu Bağlantısı:** Bu sorunun hangi alt konulara (farmakoloji, mikrobiyoloji vb.) bağlandığını göster.

---

## ── FAZ 4: OTONOM HAFIZA KAYDI (ZORUNLU) ──────────────────────

### Adım: Vektörleme & Sync

- Yanıt bittikten sonra içeriği `.md` olarak `vektörlenecek/` klasörüne kaydet.
- `scripts/dus_uploader.py --chathistory` ile senkronize et.
- Kullanıcıya "Vektörleme tamamlandı ve hafızaya eklendi" onayı ver.

---

## ── UZUN İÇERİK YÖNETİMİ ────────────────────────────────────

- Tüm bilgiler TEK YANIT olarak sunulmaya çalışılır.
- Yanıt, platformun karakter limitine yaklaşıyorsa veya çok geniş bir konu ise:
  1. Pinecone'dan tüm veriyi TEK SEFERDE çek (tekrar sorgu atma).
  2. İlk yanıtta Bölüm 1 ve Bölüm 2'nin büyük bölümünü sun.
  3. "Devam edeyim mi?" diye sor.
  4. Devam onayı gelince kalan Bölüm 2 içeriğini, tabloları ve Bölüm 3'ü (5 soru) sun.
  5. **Parçalarda bile ÖZET/KISALTMA YAPMAK KESİNLİKLE YASAKTIR.**

---

*Ders Çalışma Protokolü v8.0 | DUS Mentörü Projesi | 2026-04-28*
