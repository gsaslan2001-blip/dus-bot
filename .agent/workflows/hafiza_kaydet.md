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

### 3. Pinecone'a Upsert Et
- **Index:** `mybrain`
- **Namespace:** `dus-data`
- **Model:** multilingual-e5-large (integrated — text direkt gönder)

```python
# MCP tool: upsert-records
# name: mybrain
# namespace: dus-data
# records: [record]
```

### 4. Doğrula
Kaydın başarılı olduğunu `search-records` ile doğrula:
```python
# Arama: record id veya içerik özeti
# Sonuç döndüyse → ✅ Kayıt başarılı
```

### 5. Gemini.MD'yi Güncelle
Önemli değişiklik kaydedildiyse `Gemini.MD`'nin ilgili bölümünü güncelle.

---

## Tamamlanma Kriteri
İçerik hazırlandı + Pinecone'a upsert edildi + doğrulandı = TAMAMLANDI
