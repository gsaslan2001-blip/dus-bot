# Direktif: Pinecone'a Yeni Branş Yükle

## Hedef
Yeni bir DUS branşının PDF veya Markdown kaynaklarını `myppdfs` Pinecone indeksine yükle.

## Girdiler
- Branş adı (Türkçe, küçük harf): ör. `farmakoloji`
- Kaynak dizin: ör. `C:\Users\FURKAN\Desktop\DUS\Farmakoloji\`
- Dosya formatı: PDF veya Markdown (`.md`)

## Adım Adım Süreç

1. **Kaynak dizini doğrula** — Dosyalar mevcut mu? Kaç dosya var?
2. **Namespace boş mu kontrol et** — `describe-index-stats` ile `myppdfs`'de bu namespace var mı bak
3. **Upload scripti oluştur** — `scripts/upload_[branş]_to_pinecone.py` dosyasını yaz
   - `config.py`'den API key ve host'u al
   - Dosyaları chunk'la: `max_chars=1000`, `overlap=200`
   - Retry + exponential backoff ekle
   - Her chunk'u `myppdfs` → yeni namespace'e yükle
4. **Script'i çalıştır** — Furkan onaylarsa `python scripts/upload_[branş]_to_pinecone.py`
5. **Doğrula** — `describe-index-stats` ile namespace'deki kayıt sayısını kontrol et
6. **Bot tool'u ekle** — `scripts/dus_bot.py` ve `scripts/main.py`'ye yeni `search_[branş]()` fonksiyonu ekle
7. **Gemini.MD güncelle** — Namespace haritasını ve toplam kayıt sayısını güncelle

## Tamamlanma Kriteri
- Upload başarılı (hata yok)
- Namespace'de > 0 kayıt
- Bot tool'u aktif
- Gemini.MD güncel

## Bilinen Sorunlar
- Rate limit → Script zaten retry içeriyor, sabırla bekle
- Encoding hataları → `encoding='utf-8', errors='ignore'` kullan
