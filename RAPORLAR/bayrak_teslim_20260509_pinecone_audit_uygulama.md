# Bayrak Teslim Raporu — Pinecone Audit Uygulama

Tarih: 2026-05-09  
Klasor: `C:\Users\FURKAN\Desktop\Projeler\Pinecone`  
Durum: Audit raporu olusturuldu, uygulama kismen baslatildi, kullanici istegiyle uygulama durdurulup bayrak teslim raporu yazildi.

## 1. Bu Turda Yapilanlar

### Audit raporu

Olusturulan ana rapor:

- `RAPORLAR/proje_akisi_kapsamli_audit_20260509.md`

Icerik:

- Ana talimat dosyalari ve workflow uyumsuzluklari
- Python kod bulgulari
- Gereksiz/supheli dosyalar
- Zaman ve maliyet uzatan noktalar
- LLM'e dogrudan verilebilir fazli implementation plan

### Baseline dogrulama

Calistirildi:

```powershell
python -m compileall -q scripts bot smart_dedup_addon
```

Sonuc:

- Hata yok.
- Syntax seviyesinde proje derlenebilir durumda.
- Gercek Pinecone/OpenAI/DeepSeek API cagrisi yapilmadi.

### Kismen uygulanan kod degisiklikleri

Degisiklikler hedefli olarak asagidaki dosyalara yapildi:

- `scripts/embedding_utils.py`
- `scripts/dus_uploader.py`
- `scripts/search_engine.py`
- `scripts/anki_uploader.py`
- `scripts/anki_dedup_local.py`

Yapilanlar:

- `scripts/embedding_utils.py`
  - Provider constantlari eklendi: `PROVIDER_PINECONE`, `PROVIDER_OPENAI`, `PROVIDER_GEMINI`, `PROVIDER_LOCAL_ALIAS`.
  - Batch constantlari eklendi: `OPENAI_EMBED_BATCH_SIZE`, `PINECONE_EMBED_BATCH_SIZE`, `EMBED_RETRIES`.
  - `get_embedder("local")` artik acik sekilde deprecated alias olarak Pinecone Inference'a yonleniyor.
  - Bilinmeyen provider artik sessizce Gemini'e dusmek yerine `ValueError` firlatiyor.
  - OpenAI ve Pinecone batch embedding cagrisina basit retry wrapper eklendi.

- `scripts/dus_uploader.py`
  - Dosya aciklamasi Pinecone Inference E5 ile hizalandi.
  - `get_local_embedder` yerine `get_embedder` kullanimi getirildi.
  - Batch size 96 yapildi.
  - `embed_batch_pinecone_e5` eklendi.
  - `embed_batch_local` geriye donuk uyumluluk alias'i olarak birakildi.
  - Manifest icin `sha256` alani eklendi.
  - Degisiklik tespiti `sha256` ile yapilacak sekilde baslatildi.
  - Eski chunk silme sirasi daha guvenli hale getirildi: yeni upsert sonrasi stale old id cleanup.
  - Dry-run log'u "would embed via Pinecone E5" diye netlestirildi.

- `scripts/search_engine.py`
  - `DUSBANKASI_HOST` env/default host eklendi.
  - `_get_pinecone_index("dusbankasi")` mapping eklendi.
  - Fallback rerank hatasinda string list yerine dict list donme davranisi hizalandi.
  - Bu dosyada onceki calisma agacinda zaten Pinecone tabanli `search_questions` degisiklikleri vardi; bu turda yalniz dusbankasi host mapping netlestirildi.

- `scripts/anki_uploader.py`
  - Anki embedding aciklamasi OpenAI `text-embedding-3-large` ile hizalanmis durumda.
  - `REPORT_NAME_MARKERS` eklendi.
  - `is_card_source_json(path)` guard'i eklendi.
  - `--all` artik dedup/analysis/death_match/to_delete/temiz gibi rapor JSON'larini upload etmeye kalkmayacak sekilde filtrelenmeye baslandi.

- `scripts/anki_dedup_local.py`
  - Default threshold `0.90` yerine `0.84` yapildi.
  - Bu dosyada onceki degisikliklerden gelen `get_embedder("openai")` kullanimi korunuyor.

## 2. Kritik Notlar ve Riskler

### Dosya encoding riski

Kismi uygulama sirasinda iki dosyada BOM gorundu:

- `scripts/embedding_utils.py`
- `scripts/anki_dedup_local.py`

Bu rapor yazilmadan once BOM temizlendi. Sonraki LLM yine de diff'i kontrol etsin.

Kontrol komutu:

```powershell
git diff -- scripts/embedding_utils.py scripts/anki_dedup_local.py
```

### Dokumantasyon henuz hizalanmadi

En onemli audit bulgusu henuz uygulanmadi:

- `Gemini.MD`
- `MYBRAIN.MD`
- `MYPPDFS.MD`
- `.agent/skills/dus-mentor/SKILL.md`
- `.agent/rules/backend_rules.md`
- `.agent/rules/pinecone_rules.md`
- `.agent/workflows/*.md`
- `directives/*.md`

Bu dosyalarda hala "Yerel E5", "0 token", "CPU", "Local Embedding" gibi Pinecone-First mimariyle uyumsuz ifadeler var. Sonraki is en yuksek oncelikle bu olmali.

### Calisma agaci zaten kirliydi

Baslangicta cok sayida dosya zaten degismis veya untracked durumdaydi. Bu turda revert yapilmadi. Sonraki LLM kullanici degisikliklerini geri almamali.

Ozellikle dikkat:

- `scripts/anki_manifest.json`
- `scripts/dus_manifest.json`
- `smart_dedup_addon/manifest.json` silinmis gorunuyor
- `.claude/` ignored ama lokalde var
- `anki_jsonlar/` altinda untracked rapor/kaynak JSON karisimi var

## 3. Hemen Devam Edilecek Isler

### P0 — Dokumantasyon driftini duzelt

Asagidaki ifadeleri tek standarda cek:

- Search: `myppdfs` ve `mybrain` icin Pinecone Integrated Inference.
- Upload/fallback: `myppdfs`, `mybrain`, `chathistory`, `telos` icin Pinecone Inference API E5 1024.
- `get_embedder("local")`: deprecated alias, gercekte Pinecone Inference.
- Anki: OpenAI `text-embedding-3-large` 3072.
- Dusbankasi: OpenAI `text-embedding-3-small` 1536.

Kontrol:

```powershell
rg -n "0 token|Yerel E5|SentenceTransformers|CPU'da|CPU/GPU|Local \\(Yerel\\)" Gemini.MD README.md ANKI.MD EMBEDDING.MD MYBRAIN.MD MYPPDFS.MD .agent directives
```

Hedef:

- Sadece "deprecated/legacy" baglamlari kalsin.

### P0 — Kod derleme ve dry-run kontrollerini yeniden calistir

```powershell
python -m compileall -q scripts bot smart_dedup_addon
python scripts/search_engine.py --help
python scripts/dus_uploader.py --chathistory --dry-run
python scripts/anki_uploader.py --all --dry-run
python scripts/run_death_match.py --help
```

Not:

- `dus_uploader.py --chathistory --dry-run` API cagrisi yapmamali.
- `anki_uploader.py --all --dry-run` mevcut kodda Pinecone client init icin `PINECONE_API_KEY` isteyebilir; `.env` okunmadan calistirilirse ortam degiskeni yoksa hata verebilir. Bu beklenen olabilir, ama dry-run icin client init geciktirme daha iyi olur.

### P1 — `anki_uploader.py` dry-run ergonomisi

Su an script import/main basinda Pinecone API key kontrolu yapiyor. `--dry-run` icin bu gereksiz.

Oneri:

- Pinecone client init'i lazy yap.
- `--dry-run` modunda API key zorunlu olmasin.
- `upload_json(... dry_run=True)` embed/upsert yapmadan sadece kaynak JSON validasyonu ve sayim yapsin.

### P1 — `embedding_utils.py` format temizligi

Retry wrapper tek satir lambda ile eklendi; calisir ama okunabilirligi dusuk.

Oneri:

- OpenAI/Pinecone batch call'larini cok satirli formatla.
- `_retry_embed_call` fonksiyonunu class'lardan once veya helper bolumunde tut.
- `embed_text` icin de retry dusun.

### P1 — `dus_uploader.py` atomiklik tamamlayici

Su an sira iyilesti ama cleanup hatalari manifestte `stale_ids` olarak tutulmuyor.

Oneri:

- `delete_ids` sonuc dondursun.
- Cleanup basarisizsa `manifest[manifest_key]["stale_ids"] = stale_ids` yaz.
- Sonraki calismada stale cleanup retry edilsin.

### P1 — Bot ayarlari

Henuz uygulanmadi:

- `deepseek-chat` / `deepseek-v4-pro` callback id uyumsuzlugu
- cache key'e `speed_mode`, `search_depth`, `model` ekleme
- `rerank_enabled` toggle gercekten uygulanmiyor; ya UI'dan kaldir ya search parametresi yap
- `_detect_ders` icin Turkce karakter normalization

## 4. Sonraki LLM Icin Net Komut Sirasi

1. `git status --short --branch` ile basla.
2. `git diff -- scripts/embedding_utils.py scripts/dus_uploader.py scripts/search_engine.py scripts/anki_uploader.py scripts/anki_dedup_local.py` oku.
3. `python -m compileall -q scripts bot smart_dedup_addon` calistir.
4. Hata varsa once kismi uygulama dosyalarini duzelt.
5. Dokumantasyon driftini uygula.
6. `anki_uploader.py --all --dry-run` davranisini guvenli hale getir.
7. Bot settings/cache/rerank duzeltmelerine gec.
8. Sonunda `RAPORLAR/proje_akisi_kapsamli_audit_20260509.md` icindeki Faz 9 dogrulama listesini calistir.

## 5. Mevcut Bayrak Durumu

Calisma guvenli noktada birakildi:

- API key okunmadi/gosterilmedi.
- Gercek upsert/delete/embed API operasyonu baslatilmadi.
- Derleme baseline'i son calistirmada hatasizdi.
- Raporlama tamamlandi.

Devam edecek kisi icin ana hedef:

**Kodda baslayan Pinecone-First standardizasyonunu dokumantasyon ve bot davranisina yay; sonra dry-run/test ergonomisini tamamla.**

