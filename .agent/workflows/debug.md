# Workflow: Hata Ayıkla (`/debug`)

**Açıklama:** Projede bir hata oluştuğunda sistematik debug protokolünü uygula. Yeni kod yazmadan önce kök nedeni bul.

---

## Adımlar

### 1. Hata Bilgisini Al
- Furkan'dan tam hata mesajını (traceback) iste
- Hangi script / fonksiyon? (`dus_bot.py`, `upload_*.py`, `main.py` vb.)
- Ne zaman oluştu? (İlk kez mi? Belirli bir işlemden sonra mı?)

### 2. Kök Neden Analizi (Kod Yazmadan Önce)
Şu sırayla kontrol et:
1. **Çevre değişkenleri** → `.env` yükleniyor mu? `os.environ` doğru key'i buluyor mu?
2. **Import hataları** → Eksik paket var mı? `requirements.txt`'e eklendi mi?
3. **API bağlantısı** → Pinecone host adresi doğru mu? Token geçerli mi?
4. **Namespace hatası** → `dusbankasi`'nde `__default__` sorunu mu?
5. **Model kota aşımı** → 429 hatası mı? Fallback zinciri devreye girdi mi?
6. **Webhook çakışması** → Telegram 409 Conflict? `remove_webhook()` çalıştır

### 3. Çözüm Öner
- En basit çözümü önce dene
- Birden fazla seçenek varsa: "A planı / B planı" formatında sun
- Kodu değiştirmeden önce Furkan'dan onay al

### 4. Uygula ve Doğrula
- Değişikliği uygula
- Test et ve sonucu paylaş

### 5. Kaydet
Kritik hata ve çözümünü `mybrain/dus-data`'ya kaydet:
```
id: "debug_log-[özet]-YYYY-MM-DD"
type: "technical_decision"
```

---

## Tamamlanma Kriteri
Hata tespit edildi + kök neden belirlendi + çözüm uygulandı + doğrulandı = TAMAMLANDI
