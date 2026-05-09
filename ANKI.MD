# ANKI.MD — Anki Kart Kalite Güvencesi ve `anki` İndeks Kılavuzu

> Son güncelleme: 2026-05-03 | v1.4 — **Embedding Standardizasyonu**
> Bu kılavuz, `anki` Pinecone indeksinin yapısını, iş akışını, script API'lerini ve modern `anki-mcp` entegrasyonunu belgeler.

---

## 1. Amaç

Anki kartlarının **benzersizliğini** sağlamak ve yeni eklenen kartların mevcut koleksiyonla anlamsal olarak örtüşüp örtüşmediğini tespit etmek. Çift veya çok benzer bilgileri sınayan kartları elimine ederek kart sayısını düşürmek ve çalışma verimini artırmak.

---

## 2. Pinecone `anki` İndeksi

| Alan              | Değer                                                   |
|-------------------|---------------------------------------------------------|
| **Index Adı**     | `anki`                                                  |
| **Embedding**     | **OpenAI** — `text-embedding-3-large` (3072-dim)         |
| **Search (Query)**| **OpenAI** — `text-embedding-3-large` (3072-dim)         |

---

## 3. Is Akislari

### A. Modern Native MCP Akisi (Onerilen - Günlük Kullanım)

Asistan (Antigravity) üzerinden otonom kart yönetimi.

1. **Drafting:** Asistan ders çalışırken veya notlardan kart üretir.
2. **Smart Dedup:** Asistan, `pinecone-mcp-server` ile mevcut kartları saniyeler içinde tarar.
3. **Approval:** Benzerlik skoru %90+ olanlar kullanıcıya sunulur.
4. **Native Import:** Onaylanan kartlar `anki-mcp` (`addNotes`) ile doğrudan Anki'ye basılır.
5. **Vektör Mühürleme:** Yeni kartlar `anki_uploader.py` ile Pinecone'a kaydedilir.

### B. Toplu İçe Aktarım (Mass Import - Python Scriptleri)

Binlerce kartın aynı anda işlenmesi durumunda kullanılır.

```bash
# 1. Parse & JSON Hazırlığı
python scripts/anki_parser.py "C:\anki\yeni_kartlar.txt" --ders protez --unite unite1

# 2. Pinecone ile Dedup Analizi
python scripts/anki_dedup.py --ns protez

# 3. Kalan Benzersiz Kartları Pinecone'a ve Anki'ye Ekle
python scripts/anki_uploader.py --json anki_jsonlar/protez_unite1.json --ns protez

# (anki_uploader.py hem Pinecone upsert hem AnkiConnect import yapar)
```

---

## 4. Anki MCP Sunucusu (Antigravity Entegrasyonu)

Antigravity asistanının Anki ile doğrudan etkileşime girmesini sağlayan modern MCP katmanıdır.

### 4.1 Kullanılabilir Araçlar (Tools)

| Komut | Açıklama |
| :--- | :--- |
| `listDecks` | Desteleri ve anlık kart sayılarını listeler. |
| `addNotes` | **Toplu kart ekleme.** En hızlı native yöntem. |
| `findNotes` | Anki query diliyle kart arama (Örn: `deck:Protez is:new`). |
| `notesInfo` | Kartın ham içeriğini (HTML/Text) getirir. |
| `deleteNotes` | Hatalı veya kopya kartları Anki'den siler. |
| `sync` | AnkiWeb ile senkronizasyon yapar. |

### 4.2 Örnek Senaryolar

- *"Dünkü çalışmamızdan 5 tane Cloze kartı üret ve Anki'ye ekle."*
- *"Radyoloji destesinde 'X-ışını' geçen kartları bul ve bana göster."*
- *"Hangi destelerde bugün çok kart birikti?"*

---

## 5. Basic Kart İş Akışı (Basic-AnKing)

Bu iş akışı, klasik soru-cevap formatındaki kartların `Basic-AnKing` modeli kullanılarak Anki'ye ve Pinecone'a entegrasyonunu tanımlar.

### 5.1 Model Yapısı
- **Model Adı:** `Basic-AnKing`
- **Alanlar:**
  - `Front`: Soru veya kavram metni.
  - `Back`: Cevap ve mekanistik açıklama.
  - `BAŞLIK`: Ünite/Konu etiketi.

### 5.2 İşleme Protokolü
1.  **Hazırlık:** Girdi metni soru-cevap çiftlerine ayrılır.
2.  **Mapping:** `Front`, `Back` ve `BAŞLIK` alanları doldurulur.
3.  **Ekleme:** `anki-mcp` üzerinden `addNotes` komutuyla Anki'ye aktarılır.
4.  **Vektörleme:** Yeni kartlar **OpenAI Large (3072)** ile vektörlenip Pinecone `anki` indeksine mühürlenir.

---

## 6. Cloze Kart İş Akışı (Cloze-MAXXİNG)

Bu iş akışı, boşluk doldurma formatındaki kartların `Cloze-MAXXİNG` modeli kullanılarak işlenmesini tanımlar.

### 6.1 Model Yapısı
- **Model Adı:** `Cloze-MAXXİNG`
- **Alanlar:**
  - `Text`: Cloze marker'ları (`{{c1::...}}`) içeren ana metin.
  - `Başlık`: Ünite/Konu etiketi.
  - `Mekanizma işleyişi`: Mekanistik açıklamalar ve derinlemesine notlar.
  - `Extra`: Ek açıklamalar veya görsel notları.

### 6.2 İşleme Protokolü
1.  **Parsing:** Metin içerisindeki kritik kavramlar `{{c1::...}}` formatına dönüştürülür.
2.  **Vectorization (Vektörleme):** Pinecone'a gönderilmeden önce `Text` alanındaki Cloze marker'ları temizlenir (Örn: `{{c1::Kavram}}` -> `Kavram`). Sadece ham metin vektörlenir.
3.  **Mapping:** `Text`, `Başlık`, `Mekanizma işleyişi` ve `Extra` alanları hazırlanır.
4.  **Dedup:** Pinecone'daki mevcut `anki` indeksi ile 0.84 eşiğinde kıyaslanır.
5.  **Ekleme:** Onaylanan kartlar `anki-mcp` ile Anki'ye aktarılır.

---

## 7. Kalite Standartları

- **Deduplication Threshold:** 0.84 (tüm sistemde standart — `smart_dedup_addon`, `anki_dedup.py`, `olum_maci.md` uyumlu).
- **Format:** Cloze-MAXXİNG veya Basic-AnKing.
- **Lexical Guard:** Tip, Evre, Sınıf, Faz, Grade, Stage numaraları farklı olan kartlar anlamsal olarak benzese de ASLA kopya sayılmaz.
- **Atomic Validation:** Her `addNotes` veya `upsert` işleminden sonra `deckStats`, `findNotes` veya Pinecone hit verileriyle kullanıcıya somut kanıt sunulmalıdır. "İşlem tamam" ifadesi tek başına yetersizdir.
- **Model Confirmation:** İşleme başlamadan önce `Basic-AnKing` vs `Cloze-MAXXİNG` ayrımı kullanıcıdan teyit edilmelidir.
- **Text Preprocessing:** Vektörleme öncesi HTML etiketleri ve Cloze marker'ları (`{{c1::...}}`) temizlenir.
- **GUID Sync:** Her kartın benzersiz `guid` değeri Pinecone'da `id` olarak kullanılır. metadata'da güncel çalışma istatistikleri (`reps`, `ivl`, `due`) tutulur.

---

## 8. Dedup Script Seçim Kılavuzu

| Script | Ne Zaman Kullanılır | Yöntem | Threshold |
|---|---|---|---|
| `anki_dedup_local.py` | **Yükleme öncesi** — JSON dosyası içindeki kartları kendi aralarında karşılaştır | Pinecone Inference embed + cosine similarity | 0.84 |
| `anki_dedup.py` | **Index'te mevcut kartlarla** karşılaştırma — yeni JSON'ı var olan Pinecone verisiyle kıyasla | Pinecone index query + skor | 0.84 |
| `anki_dedup_fast.py` | Hızlı ön eleme (vektör gerekmez, API maliyeti sıfır) | Token overlap / Jaccard benzerliği | — |
| `anki_dedup_smart.py` | **LLM judge gerektiren** ince kopya tespiti — anlam benzerliği yüksek ama farklı ifadelendirilmiş kartlar | OpenAI 3-large + gpt-4o-mini judge | 0.84 |

**Önerilen Sıra (Mass Import):**
1. `anki_dedup_fast.py` → Hızlı ön eleme (bedava)
2. `anki_dedup_local.py --threshold 0.84` → JSON içi vektörel karşılaştırma
3. `anki_dedup.py --threshold 0.84` → Pinecone index'e karşı final kontrol
4. `anki_dedup_smart.py` → Sadece şüpheli çiftler için LLM hakem (maliyetli)

---

*ANKI.MD v1.5 | DUS Mentoru | 2026-05-09*
