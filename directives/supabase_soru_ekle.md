# Direktif: Supabase'e Soru Ekle

## Hedef
Üretilen DUS sorularını Supabase `questions` tablosuna embedding ile birlikte ekle.

## Girdiler
- Soru metni (Türkçe)
- Seçenekler (A, B, C, D, E)
- Doğru cevap (harf)
- Açıklama/gerekçe
- Branş (ör: `patoloji`, `endodonti`)

## Adım Adım Süreç

1. **Soru formatını doğrula** — Tüm alanlar dolu mu? Doğru cevap geçerli mi?
2. **OpenAI ile embedding üret**
   - Model: `text-embedding-3-small`
   - Input: Soru metni + seçeneklerin birleşimi
   - Boyut: 1536
3. **Supabase'e ekle**
   - Tablo: `questions`
   - Gerekli alanlar: `question_text`, `options`, `correct_answer`, `explanation`, `lesson`, `embedding`
4. **Doğrula** — Eklenen kaydı ID ile sorgula
5. **Pinecone'a da ekle (opsiyonel)** — `dusbankasi` index'ine de upsert et

## Tamamlanma Kriteri
- Supabase'de kayıt oluştu
- `match_questions_semantic` RPC ile aranabilir hale geldi

## Bilinen Sorunlar
- `dusbankasi` namespace hatası: `__default__` kullan veya `query()` ile direkt sor
- Embedding üretiminde hata: OpenAI API key'i `.env`'den oku
