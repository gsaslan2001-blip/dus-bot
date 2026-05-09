# Pinecone / DUS Mentoru Kapsamli Akis Audit Raporu

Tarih: 2026-05-09  
Kapsam: `Gemini.MD`, `README.md`, `ANKI.MD`, `EMBEDDING.MD`, `MYBRAIN.MD`, `MYPPDFS.MD`, `.agent/rules`, `.agent/workflows`, `directives`, `scripts`, `bot`, `smart_dedup_addon`, repo hijyeni.  
Not: Bu rapor kodu degistirmez; baska bir LLM'e dogrudan uygulanabilir implementation plan verir.

## 1. Yonetici Ozeti

Proje teknik olarak calisabilir durumda: `python -m compileall -q scripts bot smart_dedup_addon` hatasiz gecti. Fakat ana risk syntax degil, talimat-kod uyumsuzlugu ve operasyonel maliyet/drift.

En kritik sorunlar:

1. **Embedding mimarisi iki farkli gerceklik anlatiyor.** `EMBEDDING.MD` ve kod "yerel model yok, Pinecone Inference API var" diyor; `Gemini.MD`, `MYBRAIN.MD`, `MYPPDFS.MD`, bazi workflow ve directives dosyalari "Yerel E5 / 0 token / CPU" diyor. Bu, LLM'i yanlis rota secmeye ve maliyet/latency varsayimini yanlis kurmaya iter.
2. **Arama ayarlarinda UI ile kod arasinda kopukluk var.** Bot ayarlarinda `rerank_enabled` toggle var ama search path'leri bu flag'i dikkate almiyor. Kullanici "rerank kapali" sanabilir, sistem yine rerank yapabilir.
3. **Anki dedup pipeline'i pahali ve parcalanmis.** `anki_dedup.py`, `anki_dedup_local.py`, `anki_dedup_smart.py`, `run_death_match.py`, `clean_export_generator.py` benzer isi farkli parametre/varsayimlarla yapiyor. Bazilari hardcoded path iceriyor, bazilari esik standardindan sapmis, bazilari tum kartlari OpenAI ile yeniden embed ediyor.
4. **Hardcoded kullanici path'leri ve local-only scriptler var.** `analyze_deneme_anki.py`, `anki_dedup_smart.py`, `cikmis_ekle.py`, `daily_sync.bat` gibi dosyalar Furkan'in makinesine kilitli; bu kabul edilebilir ama "ana workflow" olarak dokumante edilirse baska LLM veya ortamda kirilir.
5. **Generated/runtime dosyalari repo ile karismis.** `.claude/worktrees` 22 MB lokal ignored durumda ama workspace'te duruyor; manifestler tracked gorunuyor ve degisiyor; `anki_jsonlar` icindeki rapor/analiz ciktisi ile kaynak JSON'lar ayni klasorde.
6. **Yikici islemler icin guard var ama standard degil.** `reset_brain.py` interaktif onay istiyor; `anki_delete.py` dry-run destekli. Fakat ortak "explicit confirmation token" standardi yok.

Ana karar onerisi:

**Tek kaynak dogrusu su olmali:**  
`myppdfs` ve `mybrain` arama = Pinecone Integrated Inference.  
`myppdfs` ve `mybrain` upload/fallback embedding = Pinecone Inference API E5 1024.  
`anki` = OpenAI `text-embedding-3-large` 3072.  
`dusbankasi` = OpenAI `text-embedding-3-small` 1536.  
Yerel SentenceTransformers artik aktif mimari degil. `get_embedder("local")` sadece backward-compatible alias ve gercekte PineconeEmbedder dondurur.

## 2. Dosya ve Akis Haritasi

Aktif katmanlar:

- `Gemini.MD`: Proje anayasasi; LLM'in ilk okuyacagi davranis/mimari talimat.
- `.agent/skills/dus-mentor/SKILL.md`: Skill router ve operasyon kilavuzu.
- `.agent/rules/*.md`: guvenlik, backend, Pinecone teknik kurallari.
- `.agent/workflows/*.md`: ders calis, soru uret, cikmis ekle, hafiza kaydet, deneme analizi/pekitirme vb.
- `scripts/embedding_utils.py`: embedding provider factory; gercek mimari burada.
- `scripts/search_engine.py`: CLI ve bot icin ana arama motoru.
- `scripts/dus_uploader.py`: `mybrain/chathistory/telos` manifest tabanli upload.
- `scripts/anki_*.py`, `scripts/run_death_match.py`: Anki parse, dedup, upload, silme, LLM judge.
- `bot/`: Telegram/FastAPI bot; intent routing, orchestrated search, DeepSeek sentez.
- `smart_dedup_addon/`: Anki eklentisi.

## 3. Talimat Dosyalarinda Uyumsuzluklar

### 3.1 Yerel E5 vs Pinecone Inference catisma

Kanıtlar:

- `EMBEDDING.MD:4`: "Yerel model tamamen kaldirildi."
- `scripts/embedding_utils.py:168-176`: default provider `pinecone`; `"local"` provider `PineconeEmbedder()` donduruyor.
- `scripts/dus_uploader.py:134-145`: fonksiyon adi `embed_batch_local`, ama `get_embedder(provider="pinecone")` kullaniyor.
- `Gemini.MD:20`, `Gemini.MD:87`, `MYBRAIN.MD:45`, `MYPPDFS.MD:67-75`, `.agent/workflows/ders_calis.md:29`, `directives/yeni_brans_ekle.md:17`, `directives/pinecone_upload.md:29`: "Yerel E5", "0 token", "CPU" iddialari var.

Etkisi:

- LLM, local SentenceTransformers indirme/kurma veya CPU embedding bekleyebilir.
- Maliyet raporu yanlis olur: Pinecone Inference "OpenAI token" harcamaz ama "tamamen maliyetsiz/yerel" de degildir.
- 429/RESOURCE_EXHAUSTED cozumleri ters yonde yazilmis: bazen "bulut embedding kullanma" deniyor, ama kod zaten Pinecone Inference kullaniyor.

Karar:

- "Yerel E5" ifadesi dokumanlarda "Pinecone Inference E5 1024" olarak degistirilmeli.
- `get_embedder("local")` docstringlerinde "deprecated alias" acik yazilmali.
- `embed_batch_local` adi `embed_batch_pinecone_e5` olarak degistirilmeli; eski ad wrapper olarak kalmali.

### 3.2 S5 pipeline kaynak kapsami catisiyor

Kanıtlar:

- `Gemini.MD:95`: ders calismada "Sadece `myppdfs` indeksi".
- `.agent/skills/dus-mentor/SKILL.md:177-185`: S5 "mybrain + myppdfs" ve Faz 2 cikmis entegrasyonu zorunlu.
- `bot/services/orchestrator.py:106-114`: `mybrain` yalniz `hafiza/genel` intent'te aranir; `ders_calis` icin aranmaz.

Etkisi:

- Ayni kullanici talebine CLI/LLM workflow ile bot farkli kaynak seti kullanabilir.
- "Hafiza" nerede devreye girer belirsiz: konu calismada mi, sadece gecmis not soruldugunda mi?

Karar:

- Ders calisma default kaynak: `myppdfs`.
- `mybrain` sadece kullanici gecmis not/strateji/hafiza isterse veya `--include-brain`/prefix kullanilirsa devreye girsin.
- Cikmis analizi ayri faz ise `dusbankasi` veya `myppdfs/cikmis` net belirtilsin.

### 3.3 Reranker zorunlu ama bot toggle'i anlamsiz

Kanıtlar:

- `bot/settings.py:51-52`: `rerank_enabled=True`.
- `bot/handlers/commands.py:201-204`: kullanici ayardan rerank ac/kapat yapabiliyor.
- `scripts/search_engine.py:84-100`, `199-222`: Integrated Search'e rerank parametresi her zaman veriliyor.
- `bot/services/orchestrator.py:71` docstring settings icinde `rerank_enabled` diyor, ama fonksiyon bunu kullanmiyor.

Etkisi:

- UI guvenilirligi bozulur.
- Maliyet/latency kontrolu bekleyen kullanici yanlis yonlendirilir.

Karar:

- Ya toggle kaldirilmali ve "reranker zorunlu" denmeli.
- Ya da `pinecone_search(..., rerank_enabled=True)` ve `search_multi_ns(..., rerank_enabled=True)` parametresi eklenip bot setting gercekten uygulanmali.
- Projenin anayasa kuralina gore onerilen: toggle kaldir, sadece `fast/balanced/comprehensive` ile `top_k/top_n` ayarla.

### 3.4 Model kimligi catisiyor

Kanıtlar:

- `Gemini.MD:74`: LLM Google Gemini 2.0-flash.
- `.agent/skills/dus-mentor/SKILL.md:54`: Gemini fallback zinciri.
- `bot/settings.py:15-16`: bot varsayilani `deepseek-v4-pro`.
- `bot/services/deepseek_client.py`: tum bot sentezi DeepSeek compatible client uzerinden.
- `scripts/run_death_match.py`: judge DeepSeek V4 Pro.

Etkisi:

- "Sistem LLM'i" ile "bot LLM'i" karisiyor.
- Baska LLM, Gemini API ile bot calistirmaya veya DeepSeek judge'i ders sentezinde kullanmaya kalkabilir.

Karar:

- Dokumanlarda iki ayrim yapilmali:
- "Agent/CLI persona LLM: kullanilan asistan ortamına bagli."
- "Production bot LLM: DeepSeek OpenAI-compatible."
- "Card judge LLM: DeepSeek/OpenAI-compatible judge."

### 3.5 Threshold standardi kaymis

Kanıtlar:

- `ANKI.MD:120`: global standard 0.84.
- `scripts/anki_dedup.py:46`: 0.84.
- `smart_dedup_addon/config.json:5`: 0.84.
- `scripts/anki_dedup_local.py:49`: default 0.90.
- `scripts/anki_dedup_smart.py:135`: `SEMANTIC_LOW = 0.94`.
- `ANKI.MD:134`: `anki_dedup_local.py` 0.84 diyor, kod 0.90.

Etkisi:

- Pipeline sirasinda bir script aday ciftleri kacirirken digeri bulabilir.
- "olum maci" judge'e giden aday sayisi dengesiz olur.

Karar:

- Tek config dosyasi: `scripts/anki_pipeline_config.json` veya Python constant module.
- Varsayilan aday esigi 0.84; "high-confidence duplicate" icin opsiyonel 0.94 etiketi.
- Tum script help/docstring/README ayni degeri kullanmali.

## 4. Python Kod Bulgulari

### 4.1 `scripts/embedding_utils.py`

Güçlü taraf:

- Provider abstraction iyi.
- `local` alias ile eski kodlar kirilmiyor.

Sorunlar:

- `GeminiEmbedder` aktif degil ama `get_embedder` bilinmeyen provider icin Gemini'e dusuyor. Bu sessiz ve tehlikeli fallback; yanlis provider typo'su 65 saniyelik sleep ve farkli maliyet dogurabilir.
- `GeminiEmbedder.embed_batch` icinde hardcoded 65s sleep var.
- OpenAI batch size 500 sabit; token/adet limit kontrolu yok.
- Pinecone batch size 96 dogruya yakin ama retry yok; upstream `dus_uploader` retry upsert icin var, embed icin yok.

Uygulama:

- Bilinmeyen provider icin `ValueError` firlat.
- Gemini provider'i explicit `provider="gemini"` ile kullanilsin ve "experimental" olarak izole edilsin.
- OpenAI/Pinecone embed batch icin tenacity retry ve batch fail isolation ekle.
- Provider isimlerini enum/constant yap.

### 4.2 `scripts/search_engine.py`

Güçlü taraf:

- Integrated Search primary, vector query fallback var.
- Host ile index baglaniyor.
- CLI query positional olarak sonda calisiyor.

Sorunlar:

- `_get_pinecone_index` `dusbankasi` icin host secmiyor; `search_questions` ayri path kullaniyor, ama genel `pinecone_search(index_name="dusbankasi")` yanlislikla `myppdfs` host'a duser.
- `search_multi_ns` integrated search'i namespace bazinda calistirip sonra global rerank yapiyor; guzel ama `pc` None ise rerank'te patlayabilir.
- `async_search_questions` Supabase RPC path'i "bakim durumunu kontrol et" diyor; production orchestrator sync Pinecone path kullaniyor. Bu eski path ya kaldirilmali ya testlenmeli.
- Return type annotation `List[str]`, gercekte dict listesi donuyor.
- `rerank_enabled` ve `DEFAULT_RERANKER_MODEL` ayarlari bot setting ile bagli degil.

Uygulama:

- `IndexName = Literal["myppdfs","mybrain","anki","dusbankasi"]` veya enum.
- `_get_pinecone_index` dusbankasi host'u da desteklesin.
- Return type `list[SearchResult]` standardize edilsin.
- Rerank parametresi opsiyonel ama default true olsun; UI toggle kaldirilacaksa kodda da comment net olsun.

### 4.3 `scripts/dus_uploader.py`

Güçlü taraf:

- Manifest tabanli delta-sync var.
- Eski chunk ID'lerini silip yeni chunk yaziyor.
- `--dry-run`, `--force`, `--chathistory`, `--telos` var.

Sorunlar:

- `mtime` ile degisiklik takip ediliyor; dosya icerigi ayni kalip timestamp degisirse gereksiz re-embed/upsert olur.
- Script aciklamasi `.claude/DUS -> mybrain`; proje icindeki `vektörlenecek/` ile bellek sync iyi, ama DUS_ROOT default'u kullanicinin home altindaki `.claude/DUS`. Bu path dokumanda net "external data root" olarak ayrilmali.
- `embed_batch_local` adi yanlis.
- Embed retry yok; batchlerden biri 429 olursa tum process yarim kalabilir.
- `delete_ids` once, embed sonra. Embed/upsert basarisiz olursa eski chunk silinmis olur. Bu atomiklik riski.

Uygulama:

- Manifest hash'i file content SHA256 ile tut; `mtime` sadece metadata olsun.
- Yeni chunklari embed etmeden eski ID silme. Sira: oku -> chunk -> embed -> upsert yeni -> manifest update -> eski id cleanup.
- Eski ID cleanup basarisizsa warning ver, manifest'te `stale_ids` tut.

### 4.4 Anki dedup/uploader pipeline

Dosyalar:

- `anki_parser.py`: TXT -> normalized JSON.
- `anki_dedup_fast.py`: token/Jaccard, bedava on eleme.
- `anki_dedup_local.py`: JSON ici OpenAI embedding + torch matrix.
- `anki_dedup.py`: local JSON kartlarini Pinecone `anki` index'e karsi sorgular.
- `anki_dedup_smart.py`: hardcoded file ile OpenAI judge.
- `run_death_match.py`: DeepSeek judge, rapor ve temiz TXT.
- `anki_uploader.py`: JSON -> Pinecone `anki`.
- `anki_delete.py`: AnkiConnect + Pinecone delete.

Sorunlar:

- `anki_dedup_smart.py` hardcoded `C:\Users\FURKAN\Desktop\Projeler\anki\endo full.txt` kullaniyor; genel workflow'a uygun degil.
- `anki_dedup_local.py` aciklamasi "Yerel" ama OpenAI embedding kullaniyor; `torch` sadece matrix similarity icin.
- `anki_dedup.py` her kart icin tekrar OpenAI embed + Pinecone query yapiyor. Buyuk batchte pahali ve yavas; manifest/cache yok.
- `anki_uploader.py --all` tum JSON'lari topluyor ama sadece `_dedup_report.json` dosyalarini disliyor; `deneme_analizi.json`, analiz raporlari veya kaynak olmayan JSON'lar yanlislikla upload edilebilir.
- `anki_uploader.py` dokumani "hem Pinecone upsert hem AnkiConnect import yapar" diyor (`ANKI.MD`), kod sadece Pinecone upsert yapiyor.

Uygulama:

- Tek CLI orkestrator yaz: `scripts/anki_pipeline.py`.
- Alt komutlar: `parse`, `fast-dedup`, `internal-dedup`, `index-dedup`, `judge`, `export-clean`, `upload`, `delete`.
- Tum threshold/model/path degerleri tek configten gelsin.
- `anki_uploader.py --all` yalniz `*_source.json` veya manifestte `type=cards` olan dosyalari alsin; rapor/analiz JSON'larini asla upload etmesin.
- OpenAI embedding cache ekle: `scripts/cache/anki_embeddings.sqlite` veya JSONL sha256 -> vector metadata. Buyuk kart setlerinde tekrar maliyeti duser.
- `anki_dedup_smart.py` deprecated yap veya `run_death_match.py` ile birlestir.

### 4.5 `scripts/run_death_match.py`

Güçlü taraf:

- Reasoning model token problemi iyi belgelenmis.
- Retry, concurrency, resume/retry-errors var.
- Markdown + JSON + temiz TXT uretimi guzel.

Sorunlar:

- `MAX_TOKENS` default 8000. Her cift icin cok yuksek token tavanı; reasoning modelde maddi maliyet artirir.
- Prompt her cift icin tam tekrar gidiyor. Cok sayida ciftte fixed prompt tokenlari maliyet yaratir.
- Pair batching yok; her pair tek chat completion.

Uygulama:

- Varsayilan `MAX_TOKENS=1200-2000` ile basla; bos yanit gorulurse adaptive retry'da 4000/8000'e cik.
- Judge promptunu kisalt ve karar formatini JSON'a cevir.
- `--max-pairs`, `--estimate-cost`, `--dry-run-cost` ekle.

### 4.6 `scripts/analyze_deneme_anki.py`

Sorunlar:

- Hardcoded deneme dosyasi path'i var.
- Namespace listesi sabit.
- Output `vektörlenecek/` altina dogrudan yaziliyor; rapor dosyasi ile chathistory staging karisiyor.
- Rerank match'i `metadata.text` string equality ile orijinal match'e baglaniyor; ayni text varsa namespace kayabilir.

Uygulama:

- CLI args: `--input`, `--out-dir`, `--namespaces`, `--top-k`, `--top-n`, `--json`.
- Match referansi icin candidate listesine `candidate_id` ekle, rerank sonucunu index ile map et.
- Output'u `RAPORLAR/generated/deneme_analizi/` altina yaz; chathistory'e kopyalama ayri flag olsun.

### 4.7 Bot katmani

Güçlü taraf:

- Intent routing + orchestrated parallel search + direct synthesis mantigi iyi.
- Search cache var.
- Chat turn staging non-blocking.

Sorunlar:

- `bot/settings.py` zorunlu env'leri import aninda `os.environ[...]` ile okuyor; eksik env bot importunu patlatir. Production icin iyi, test/CLI icin sert.
- `bot/services/deepseek_client.py` `deepseek` None ise daha acik hata vermiyor.
- `bot/services/agent_loop.py` fast mode tool loop'u kapatiyor; bu bilincli, ama "source-grounded" cevap kalitesi dusurebilir.
- `bot/services/orchestrator.py` `_detect_ders` Turkce karakter normalization yapmiyor; `diş eti`, `köprü`, `kök kanal` gibi girdiler kacabilir.
- Bot settings'te `model="deepseek-v4-pro"` ama command callback'te "V4 Pro" callback'i `deepseek-chat` gonderiyor (`bot/handlers/commands.py`), AVAILABLE_MODELS ile uyumsuzluk olabilir.

Uygulama:

- Settings icin `pydantic-settings` veya basit `validate_settings()` ekle.
- `_detect_ders` icin Unicode normalization ve synonym listesi.
- Callback model id'lerini `AVAILABLE_MODELS` keys ile birebir yap.
- Cache key'e `speed_mode/search_depth/model` ekle; su an sadece query/intent/forced_index var, ayar degisince eski cache kullanilabilir.

## 5. Gereksiz / Supheli / Ayrilmasi Gereken Dosyalar

Silmeden once onay alinmali. Onerilen aksiyonlar:

### Arsiv / legacy

- `archive/dus_bot_v6.py`: Eski monolit bot. Tutulacaksa `archive/README.md` icinde "legacy snapshot, active degil" diye isaretle. Aktif import yoksa kalabilir.
- `.claude/worktrees/`: `.gitignore` icinde ignored; lokalde 22 MB. Aktif proje analizine dahil edilmemeli. Gerekirse local temizlenebilir ama repo aksiyonu degil.

### Generated/runtime state

- `scripts/anki_manifest.json`, `scripts/dus_manifest.json`: `.gitignore` icinde ama tracked/değişmiş gorunuyor. Runtime state ise repodan cikarmak icin `git rm --cached` uygulanmali.
- `anki_jsonlar/*_dedup_report.*`, `*_smart_dedup_report.*`, `*_fast_dedup_report.*`, `*_death_match*`, `*_to_delete.txt`: output klasorune tasinmali veya ignored olmali.
- `RAPORLAR/generated/`: yeni generated raporlar buraya gitsin.

### Hardcoded deney scriptleri

- `scripts/_test_quickjudge.py`: test/smoke script; `scripts/dev/` altina tasinmali veya pytest'e cevrilmeli.
- `scripts/analyze_deneme_anki.py`: aktif workflow'a alinacaksa CLI parametreli hale getirilmeli; yoksa `scratch/`/`archive/` altina alinmali.
- `scripts/anki_dedup_smart.py`: `run_death_match.py` ile overlap ediyor ve hardcoded path iceriyor. Deprecated yap.
- `scripts/download_model.py`: Yerel model kaldirildigi icin ya silinmeli ya da README'de "legacy, kullanma" denmeli.

## 6. Maliyet ve Zaman Uzatan Noktalar

1. `run_death_match.py` default `MAX_TOKENS=8000`: Pair basina tavan cok yuksek. Adaptive token retry ile dusur.
2. `anki_dedup.py`: Her kart icin OpenAI embed + Pinecone query; embedding cache ve once fast/local prefilter olmadan pahali.
3. `anki_dedup_local.py`: Tum pair similarity matrisi O(n^2) memory/time. 5k kartta 25M skor; chunked/top-k FAISS benzeri yaklasim daha iyi.
4. `GeminiEmbedder`: 65s sleep hardcoded; bilinmeyen provider typo'su bu yola dusmemeli.
5. `dus_uploader.py`: mtime tabanli manifest gereksiz re-embed yaratabilir.
6. `search_multi_ns`: Her namespace icin ayri Integrated Search. Cok namespace + top_k yuksekse hiz/maliyet artar; intent/ders detection iyilestirilmeli.
7. Chat history zorunlu sync her yanitta `dus_uploader.py --chathistory` calistirma talimati operasyonel olarak pahali/yavas; bot su an sadece staging dosyasi yaziyor. Batch sync dogru davranis.

## 7. Tavsiye Edilen Nihai Akislar

### 7.1 Ders calisma

1. Intent/ders tespit et.
2. Default yalniz `myppdfs/<ders>` ara; cross namespace sadece kural tablosunda gerekliyse.
3. Integrated Search `top_k=15`, rerank `top_n=5`.
4. Kaynak yoksa "bilmiyorum/dogrulayalim"; tahmin yok.
5. Sentez yap.
6. Chat turn'u `vektörlenecek/` altina staging olarak yaz.
7. Sync batch/gun sonu: `python scripts/dus_uploader.py --chathistory`.

### 7.2 Anki mass import

1. `anki_parser.py` ile TXT -> normalized card JSON.
2. `anki_dedup_fast.py` ile bedava kaba on eleme.
3. `anki_dedup_local.py --threshold 0.84` ile JSON ici aday ciftler.
4. `run_death_match.py --estimate-cost` ile maliyet tahmini.
5. `run_death_match.py --threshold 0.84 --concurrency 2/3` ile sadece aday ciftleri judge'e gonder.
6. `clean_export_generator.py` veya unified export ile temiz TXT uret.
7. Kullanici onayi sonrasi Anki import.
8. `anki_uploader.py --json ... --ns ...` ile Pinecone `anki` muhuru.

### 7.3 Deneme analizi

1. Deneme aciklama dosyasini argumanla al.
2. Her soru icin OpenAI 3072 embed -> `anki` namespaces query.
3. Adaylari global rerank.
4. Raporu `RAPORLAR/generated/deneme_analizi/<date>/` altina yaz.
5. Kullanici isterse ozet chathistory staging'e yaz ve batch sync.

## 8. Implementation Plan: Baska LLM'e Verilecek Uygulama Talimati

Asagidaki adimlari sirasiyla uygula. Kod degistirirken mevcut user degisikliklerini geri alma. Her adim sonunda compile/test komutunu calistir.

### Faz 0 - Guvenlik ve baseline

1. `git status --short --branch` al; mevcut degisiklikleri not et, hicbirini revert etme.
2. `.env` dosyasini okuma.
3. `python -m compileall -q scripts bot smart_dedup_addon` baseline olarak calistir.
4. Yeni test/rapor outputlarini `RAPORLAR/generated/` veya `scratch/` altina yaz.

### Faz 1 - Mimari tek kaynak dogrusu

1. `EMBEDDING.MD`'yi canonical mimari belgesi yap.
2. `Gemini.MD`, `MYBRAIN.MD`, `MYPPDFS.MD`, `.agent/skills/dus-mentor/SKILL.md`, `.agent/rules/backend_rules.md`, `.agent/rules/pinecone_rules.md`, `.agent/workflows/*.md`, `directives/*.md` icindeki "Yerel E5", "0 token", "CPU/GPU", "SentenceTransformers" ifadelerini su standarda cevir:
   - Search: Pinecone Integrated Inference.
   - Upload/fallback for myppdfs/mybrain/chathistory/telos: Pinecone Inference API E5 1024.
   - `get_embedder("local")`: deprecated alias for Pinecone Inference.
   - Anki: OpenAI `text-embedding-3-large` 3072.
   - Dusbankasi: OpenAI `text-embedding-3-small` 1536.
3. README'de `download_model.py` icin "legacy/local model removed" notu ekle veya dosyayi archive planina al.
4. Versiyon notlarini v8.9/v5.0 karmasasindan kurtar: "2026-05-09 canonical Pinecone-First standard" ekle.

Kabul kriteri:

- `rg -n "0 token|Yerel E5|SentenceTransformers|CPU'da|CPU/GPU|Local \\(Yerel\\)" *.MD .agent directives` ciktisinda sadece "deprecated/legacy" baglamlari kalir.

### Faz 2 - Embedding provider refactor

Dosya: `scripts/embedding_utils.py`

1. Provider constantlari ekle: `PROVIDER_PINECONE`, `PROVIDER_OPENAI`, `PROVIDER_GEMINI`, `PROVIDER_LOCAL_ALIAS`.
2. `get_embedder(provider="pinecone", dimension=None)` bilinmeyen provider icin `ValueError` firlatsin.
3. `"local"` geldiginde warning logla: "deprecated alias; using Pinecone Inference".
4. `GeminiEmbedder` sadece explicit `"gemini"` icin kullanilsin.
5. `OpenAIEmbedder.embed_batch` ve `PineconeEmbedder.embed_batch` icin retry/backoff ekle.
6. Batch size degerlerini module constants yap.

Kabul kriteri:

- `python -m compileall -q scripts`
- `python - <<'PY'\nfrom scripts.embedding_utils import get_embedder\ntry:\n    get_embedder('typo')\nexcept ValueError:\n    print('ok')\nPY`

### Faz 3 - `dus_uploader.py` atomiklik ve hash

Dosya: `scripts/dus_uploader.py`

1. `embed_batch_local` adini `embed_batch_pinecone_e5` yap; eski isim wrapper olarak kalsin.
2. Manifest'e `sha256` ekle; degisiklik kontrolunu `mtime` yerine sha256 ile yap.
3. `process_file` sirasini degistir:
   - dosyayi oku
   - sha256 hesapla
   - degismediyse skip
   - chunkla
   - embed et
   - yeni vectorleri upsert et
   - manifest update et
   - eski id'leri cleanup et
4. Cleanup basarisizsa manifest'te `stale_ids` tut ve log warning ver.
5. `--dry-run` output'una "would embed N chunks" ekle.

Kabul kriteri:

- `python scripts/dus_uploader.py --chathistory --dry-run`
- Manifest format eski kayitlari okuyabilmeli.

### Faz 4 - Search engine standardization

Dosya: `scripts/search_engine.py`

1. `SearchResult` typed dict/dataclass ekle: `text`, `score`, `source`, `namespace`, `id`.
2. `_get_pinecone_index("dusbankasi")` host mapping ekle.
3. Return type annotationlari dict listesine uygun hale getir.
4. `rerank_enabled` parametresi ekle veya UI toggle kaldirilacaksa kod commentleri temizle.
5. `search_questions` icin `limit` kadar raw result query yapildiktan sonra opsiyonel rerank uygula; workflow `deneme_pekitirme.md` rerank zorunlu diyorsa gercekte de uygula.
6. `async_search_questions` Supabase RPC path'ini deprecated olarak isaretle veya orchestrator'dan tamamen ayir.

Kabul kriteri:

- `python -m compileall -q scripts bot`
- `python scripts/search_engine.py --help`
- API gerektirmeyen unit testlerde `_get_pinecone_index` mocklanarak dusbankasi mapping test edilir.

### Faz 5 - Bot settings ve cache fix

Dosyalar: `bot/settings.py`, `bot/handlers/commands.py`, `bot/services/orchestrator.py`, `bot/main.py`

1. `AVAILABLE_MODELS` keyleri ile callback model id'lerini birebir esitle.
2. `deepseek-chat` ile `deepseek-v4-pro` karmasasini coz.
3. Search cache key'e `speed_mode`, `search_depth`, `model`, `forced_index` ekle.
4. `rerank_enabled` toggle kaldirilacaksa UI'dan sil; kalacaksa orchestrator/search_engine'e parametre olarak gec.
5. `_detect_ders` icin Turkce karakter normalization helper ekle.

Kabul kriteri:

- `python -m compileall -q bot`
- `/settings` callbackleri unavailable model id uretmez.

### Faz 6 - Anki pipeline sadeleştirme

Yeni dosya: `scripts/anki_pipeline_config.py` veya `scripts/anki_pipeline_config.json`  
Opsiyonel yeni dosya: `scripts/anki_pipeline.py`

1. Global config:
   - `DEFAULT_DUP_THRESHOLD = 0.84`
   - `HIGH_CONFIDENCE_DUP_THRESHOLD = 0.94`
   - `OPENAI_EMBED_MODEL = "text-embedding-3-large"`
   - `ANKI_DIM = 3072`
   - allowed source JSON glob patterns.
2. `anki_dedup_local.py` default threshold'i 0.84 yap.
3. `anki_dedup.py` comments'teki "Yerel E5" ifadesini OpenAI Large olarak duzelt.
4. `anki_uploader.py --all` sadece card source JSON'larini upload etsin:
   - dedup/report/analysis/death_match/to_delete dosyalarini kesin disla.
   - JSON icindeki ilk kayitta `guid`, `vektorlenecek_metin`, `kart_tipi` yoksa skip.
5. `anki_dedup_smart.py` hardcoded path'i kaldir:
   - CLI args `--txt`, `--threshold`, `--out-dir`.
   - Ya da dosyanin basina "DEPRECATED: use run_death_match.py" yaz ve README'den kaldir.
6. `run_death_match.py`:
   - `--estimate-cost` ekle.
   - Default max tokens'i dusur; bos response retry'da artir.
   - `--max-pairs` ekle.
7. `clean_export_generator.py` ile `run_death_match.py` export mantigini birlestirmeyi planla; simdilik README'de net ayrim yaz.

Kabul kriteri:

- `python scripts/anki_parser.py --help`
- `python scripts/anki_dedup_local.py --help` default threshold 0.84 gosterir.
- `python scripts/anki_uploader.py --all --dry-run` rapor JSON'larini upload etmeye kalkmaz.

### Faz 7 - Deneme analizi scriptini production hale getir

Dosya: `scripts/analyze_deneme_anki.py`

1. Hardcoded input path'i kaldir.
2. CLI args ekle:
   - `--input`
   - `--out-dir` default `RAPORLAR/generated/deneme_analizi`
   - `--namespaces`
   - `--top-k`
   - `--top-n`
   - `--stage-chathistory`
3. Rerank result mapping'i text equality yerine candidate index/id ile yap.
4. Her soru raporunu tek tek `vektörlenecek/` altina yazmak yerine rapor klasorune yaz; `--stage-chathistory` verilirse ozet staging'e kopyala.

Kabul kriteri:

- `python scripts/analyze_deneme_anki.py --help`
- Input yoksa acik hata mesaji.

### Faz 8 - Repo hijyeni

1. `.gitignore` zaten `.claude/`, manifests, logs ve generated bazi ciktıları ignore ediyor. Tracked manifestleri repodan cikarmak icin kullanicidan onay al:
   - `git rm --cached scripts/anki_manifest.json scripts/dus_manifest.json`
2. `RAPORLAR/generated/` altini generated rapor standardi yap.
3. `anki_jsonlar/` icin klasor ayrimi oner:
   - `anki_jsonlar/source/`
   - `anki_jsonlar/reports/`
   - `anki_jsonlar/exports/`
4. `.claude/worktrees` local ignored; silme ancak kullanici onayi ile yap.

Kabul kriteri:

- `git status --short` sadece beklenen kod/dokuman degisikliklerini gosterir.
- Runtime dosyalari yeni commit'e girmez.

### Faz 9 - Test ve doğrulama

1. `python -m compileall -q scripts bot smart_dedup_addon`
2. `python scripts/search_engine.py --help`
3. `python scripts/dus_uploader.py --chathistory --dry-run`
4. `python scripts/anki_uploader.py --all --dry-run`
5. `python scripts/run_death_match.py --help`
6. `rg -n "Yerel E5|0 token|SentenceTransformers|CPU'da|deepseek-chat|0\\.90|C:\\\\Users\\\\FURKAN\\\\Desktop\\\\Projeler\\\\anki\\\\endo full.txt" Gemini.MD README.md ANKI.MD EMBEDDING.MD MYBRAIN.MD MYPPDFS.MD .agent directives scripts bot`
7. API kullanan testleri dry-run/mocked calistir; gercek Pinecone/OpenAI/DeepSeek cagrisini kullanicidan onay almadan baslatma.

## 9. Onceliklendirilmis Yol Haritasi

P0 - Hemen:

- Talimat dosyalarindaki embedding catisma dilini duzelt.
- `anki_uploader.py --all` guard ekle.
- `anki_dedup_local.py` threshold defaultunu 0.84 yap.
- `analyze_deneme_anki.py` ve `anki_dedup_smart.py` hardcoded path'lerini kaldir veya deprecated isaretle.

P1 - Kisa vadeli:

- `dus_uploader.py` sha256 + atomik upsert refactor.
- `search_engine.py` return type ve dusbankasi host mapping.
- Bot model callback/cache/rerank ayarlarini duzelt.

P2 - Orta vadeli:

- Unified `anki_pipeline.py`.
- Embedding cache.
- Cost estimator for death match.
- Generated artifact klasor standardi.

## 10. Son Karar

Proje guclu bir cekirdege sahip: Pinecone Integrated Search, manifest tabanli upload, Anki OpenAI mirror mode ve DeepSeek judge akli dogru yonler. Ana sikinti "cok hizli evrimlesmis sistemlerde gorulen dokuman-kod drift'i". Bunu tek canonical embedding standardi, tek Anki pipeline config'i ve runtime/generated dosya ayrimi ile temizlersen sistem hem daha ucuz hem daha hizli hem de LLM'ler icin cok daha az yanlis anlasilir hale gelir.

