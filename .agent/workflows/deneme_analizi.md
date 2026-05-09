# İş Akışı: /deneme-analizi

## 1. Amaç
Kullanıcının deneme sınavlarında yanlış yaptığı soruların yer aldığı md formatındaki açıklamaların analiz edilerek, ilgili konular hakkında Anki veritabanımızda (Pinecone) ne kadar ve hangi kartların olduğunun tespit edilmesi. 
Bu süreç sayesinde kullanıcının eksik olduğu noktalarla ilgili Anki'de çalışabileceği materyalleri otomatik olarak saptamak ve bunları atomik, incelenebilir raporlar halinde saklamak amaçlanmaktadır.

## 2. Kullanım Şartları (Trigger)
Kullanıcı "Bu iş akışını çalıştır: deneme analizi" dediğinde veya yanlış yaptığı soruları içeren bir markdown metni verip, "Bu soruları anki'de incele" talebinde bulunduğunda tetiklenir.

## 3. Çalışma Prensipleri

1. **Soruların Ayrıştırılması**: 
   - Verilen metin `\n\n` (boş satırlar) veya soru numaralandırma formatına göre ayrıştırılır. 
   - Her soru/açıklama bloğu ayrı bir analiz nesnesi olarak ele alınır.

2. **OpenAI API Vektörleme (Embedding)**:
   - Anki indeksi `OpenAI Large (3072-dim)` mimarisini kullandığı için, her sorunun metni Pinecone'a gönderilmeden önce `scripts/embedding_utils.py` içerisindeki `get_embedder(provider="openai", dimension=3072)` fonksiyonu ile **OpenAI API'ye** gönderilerek vektörlenir. (Yerel/offline model yok.)

3. **Anki İndeksinde Kapsamlı Arama (Multi-Namespace)**:
   - Üretilen vektör, `anki` indeksindeki mevcut tüm ders isim alanlarında (namespaces) eşzamanlı/sıralı olarak (`protez`, `fizyoloji`, `endodonti`, `patoloji`, `radyoloji`, `histoloji`, `periodontoloji` vb.) `top_k=5` parametresiyle aranır.
   - Bulunan tüm aday sonuçlar tek bir havuzda toplanır.

4. **Yeniden Sıralama (Reranking)**:
   - Tüm namespace'lerden toplanan sonuçlar en yüksek Pinecone skorlarına göre filtrelenir (örneğin en iyi 15).
   - Pinecone Inference API üzerindeki `bge-reranker-v2-m3` modeli kullanılarak, sorunun metni ile aday kartlar reranking işlemine tabi tutulur ve pedagojik/anlamsal olarak en yakın ilk 5 kart kesinleştirilir.

5. **Atomik MD Raporlama ve Vektörlenecek Klasörü**:
   - Analiz edilen her bir soru için `vektörlenecek/` klasörü altında ayrı bir markdown dosyası oluşturulur (Örn: `vektörlenecek/deneme_analizi_09052026_soru_1.md`).
   - Bu dosyada yer alanlar:
     - Sorunun orijinal metni
     - Bulunan Anki kartlarının toplam sayısı
     - Her kartın bulunduğu ders (namespace), Rerank skoru, Ön yüzü (Front), Arka yüzü (Back), Etiketleri (Tags) ve tam metni.
   - Bu raporlar, ilerleyen aşamada `dus_uploader.py --chathistory` komutuyla geçmiş hafızasına kazınabilmeye hazır formatta tutulur.

## 4. Teknik Yığın ve Scriptler
Bu işlem `scripts/analyze_deneme_anki.py` scripti üzerinden yürütülür. Komut:
```bash
python scripts/analyze_deneme_anki.py
```
**⚠️ Script mevcut değilse:** `scripts/` dizininde bu adla yeni bir script oluştur — `embedding_utils.py` ve `search_engine.py` bağımlılıklarını kullan. Geçici/anonim betik yazma; kalıcı dosya oluştur.
