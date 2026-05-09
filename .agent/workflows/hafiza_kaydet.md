# Workflow: Hafıza Kaydet (`/hafiza-kaydet`)

**Açıklama:** Mevcut sohbetin önemli kararlarını veya tüm içeriğini Pinecone'a kalıcı olarak kaydet.

---

## Adımlar

### 1. Ne Kaydedileceğini Belirle
Furkan şunu diyorsa:
- **"konuştuklarımızı kaydet"** → Tüm sohbet akışını kaydet
- **"bu kararı kaydet"** → Sadece belirtilen kararı kaydet
- **"oturum sonu"** → Yapılan işlemlerin özetini kaydet

### 2. İçeriği Hazırla

#### Tam Sohbet Kaydı:
```python
record = {
    "id": f"session_full_log-{YYYY}-{MM}-{DD}-{HHMM}",
    "text": "<o ana kadarki tüm sohbet akışı>",
    "source": "antigravity_session",
    "type": "session_full_log",
    "date": "YYYY-MM-DD"
}
```

#### Mimari Karar Kaydı:
```python
record = {
    "id": f"architecture_decision-{özet}-{YYYY}-{MM}-{DD}",
    "text": "<karar içeriği ve gerekçesi>",
    "source": "antigravity_session",
    "type": "architecture_decision",
    "date": "YYYY-MM-DD"
}
```

#### Teknik Karar Kaydı:
```python
record = {
    "id": f"technical_decision-{özet}-{YYYY}-{MM}-{DD}",
    "text": "<teknik karar + çözüm>",
    "source": "antigravity_session",
    "type": "technical_decision",
    "date": "YYYY-MM-DD"
}
```

### 3. Pinecone'a Aktar (Staging & Sync)
DUS Mentörü mimarisi gereği doğrudan `upsert-records` yerine staging mekanizması kullanılır:

1. **Staging:** Hazırlanan içeriği `.md` dosyası olarak `vektörlenecek/` klasörüne kaydet.
   - Dosya adı formatı: `YYYYMMDD_konu_ozeti.md`
2. **Sync:** `scripts/dus_uploader.py --chathistory` komutunu çalıştır.
   - Bu işlem Pinecone Inference E5 (`get_embedder("pinecone")`) kullanarak veriyi `chathistory` namespace'ine mühürler.
3. **Akademik Not ise:** Eğer kaydedilen bilgi bir ders notu ise `memory/` klasörüne kaydet ve `dus_uploader.py` (flagsiz) çalıştırarak `dus-memory`'ye aktar.

### 4. Doğrula
Kaydın başarılı olduğunu Integrated Search ile sorgula:
```python
# mcp_pinecone-mcp-server_search-records
# name: mybrain
# namespace: chathistory
# query: <kaydedilen konu özeti>
```

### 5. Gemini.MD'yi Güncelle
Eğer mimari veya stratejik bir karar alındıysa `Gemini.MD`'nin ilgili bölümünü ve versiyon numarasını güncelle.

---

## Tamamlanma Kriteri
İçerik staging klasörüne yazıldı + `dus_uploader.py` ile Pinecone'a sync edildi + doğrulandı = TAMAMLANDI
