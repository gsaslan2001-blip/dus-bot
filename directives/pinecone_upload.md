# Direktif: Pinecone'a Genel Veri Yükle

## Hedef
Herhangi bir metin verisini (markdown, düz metin) Pinecone'a chunk'layarak yükle.

## Girdiler
- Kaynak dosya veya dizin yolu
- Hedef index adı: `mybrain` veya `myppdfs`
- Hedef namespace
- Chunk parametreleri (varsayılan: max_chars=1000, overlap=200)

## Adım Adım Süreç

1. **Dosyayı oku** — UTF-8 encoding, errors='ignore'
2. **Chunk'la** — max_chars ve overlap değerleriyle böl
3. **ID üret** — `{kaynak_dosya_adı}-chunk-{n}` formatında
4. **Metadatayı hazırla** — source, type, date
5. **Toplu yükle** — `upsert_records` ile batch=100 olarak gönder
6. **Rate limit koruması** — Hata alırsan 60 saniye bekle, tekrar dene (max 3 deneme)
7. **Doğrula** — `describe-index-stats` ile namespace kayıt sayısını kontrol et

## Tamamlanma Kriteri
- Tüm chunk'lar yüklendi (hata yok)
- Namespace'de beklenen kayıt sayısı var
- `search-records` ile aranabilir

## Notlar
- `mybrain` ve `myppdfs`: Integrated inference — text direkt gönder, embedding otomatik üretilir
- `dusbankasi`: Integrated inference YOK — OpenAI ile önce embed üret
