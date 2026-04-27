# Backend Kuralları — DUS Mentörü

> Bu kurallar her zaman aktiftir. İstisna kabul edilmez.

## 1. API Anahtarı Güvenliği
- API anahtarları **ASLA** koda yazılmaz (hardcode yasak)
- Her zaman `os.environ.get("KEY_NAME")` kullan
- `.env` dosyasını oku, yazma, silme veya içeriğini gösterme
- Yeni script yazarken dosyanın başına `from dotenv import load_dotenv; load_dotenv()` ekle

## 2. Pinecone Bağlantı Kuralları
- Index'lere **isimle değil, host adresiyle** bağlan:
  ```python
  # DOĞRU:
  index = pc.Index(host="https://myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io")
  # YANLIŞ:
  index = pc.Index("myppdfs")
  ```
- `mybrain` ve `myppdfs`: **Yerel E5 (Local Embedding)** — Sorgu önce yerel CPU'da vektörlenir, sonra vektör gönderilir.
- `dusbankasi`: OpenAI ile embedding üret, sonra Pinecone'a gönder.

## 3. Hata Yönetimi
- Upload scriptlerinde **retry + exponential backoff** zorunlu (rate limit koruması)
- Her API çağrısını try/except ile sar
- Hata logları konsola yazılır ama kullanıcıya gösterilmez (bot yanıtında sadece özet)

## 4. Reranker Zorunluluğu
- Tüm Pinecone aramalarında `bge-reranker-v2-m3` reranker'ı kullan
- `topK=20` ile sorgula, `topN=5` ile rerank et
- Reranker olmadan sonuç döndürme

## 5. Chunk Parametreleri (Standart)
```python
max_chars = 1000
overlap = 200
```
Bu parametreler tüm upload scriptlerinde sabit kalır.

## 6. Namespace İzolasyonu
- Her branş kendi namespace'inde tutulur (karışma riski yok)
- Yeni branş eklerken yeni namespace aç, `dus-data` veya `claude_memory`'ye veri ekleme

## 7. Kod Değişikliği Sonrası
- Önemli değişiklikleri `Gemini.MD`'nin "Görev Kuyruğu" veya "Oturum Raporu" bölümüne yaz
- Mimari karar aldıysan `mybrain/dus-data`'ya kaydet
