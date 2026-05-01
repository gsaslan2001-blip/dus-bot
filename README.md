# 🧠 DUS Mentörü — Proje Rehberi (README)

> **⚠️ LLM ONBOARDING:** Bu proje, DUS 2026 sınavına hazırlanan öğrenciler için geliştirilmiş, **mekanizma odaklı** bir tıp/diş hekimliği eğitim asistanıdır. Proje, tamamen **local-first** (yerel öncelikli) bir RAG (Retrieval-Augmented Generation) mimarisi üzerine kuruludur.
> **Güncellenme:** 2026-04-27 | **Versiyon:** v8.2 (S5 Pipeline Standardizasyonu)

---

## 1. Projenin Amacı ve Kapsamı
DUS Mentörü, diş hekimliği öğrencilerinin ezberden uzak, patofizyolojik mekanizmalar üzerinden ders çalışmasını sağlayan bir yapay zeka sistemidir. Branş notlarını (`myppdfs`), kişisel hafıza katmanlarını (`mybrain`) ve binlerce çıkmış soruyu (`dusbankasi`) semantik olarak tarayarak yüksek hassasiyetli akademik içerik ve özgün soru üretir.

---

## 2. Temel Mimari ve Sistem Akışı (S5 Pipeline)
Proje, bulut kotalarından bağımsız çalışmak için hibrit bir yapı kullanır:

1.  **Sorgu İşleme:** Kullanıcı sorusu yerel CPU/GPU üzerinde `multilingual-e5-large` modeli ile vektörlenir.
2.  **Retrieval (Arama):** Oluşturulan vektör Pinecone Serverless (AWS us-east-1) üzerinde çoklu namespace taranarak en ilgili 15 parça çekilir.
3.  **Reranking (Yeniden Sıralama):** Çekilen parçalar `bge-reranker-v2-m3` API'sinden geçirilerek en alakalı 5 parça seçilir.
4.  **Sentez ve Sunum:** Seçilen parçalar, akademik bir üslup ve mekanizma odaklı anlatımla kullanıcıya sunulur.
5.  **Zorunlu Hafıza Kaydı:** Her yanıt anında `vektörlenecek/` klasörüne staging olarak kaydedilir ve periyodik olarak Pinecone `chathistory` namespace'ine aktarılır (Mandatory Sync Protocol).

---

## 3. Dosya Hiyerarşisi

```text
Pinecone/
├── .agent/              # Ajan kuralları ve iş akışları (Rules/Workflows)
├── .env                 # API Anahtarları (Pinecone, OpenAI, Supabase)
├── CIKMIS_SORULAR.MD    # Çıkmış soru dataseti (2015-2026) kılavuzu
├── DUSBANKASI.MD        # 16K+ soruluk Supabase/Pinecone soru bankası rehberi
├── EMBEDDING.MD         # Yerel E5 ve Reranker teknik mimari rehberi
├── Gemini.MD            # Proje Anayasası (v8.2), kimlik ve kesin kurallar
├── LLM_ONBOARDING_RAPORU.md # Kapsamlı sistem analizi ve risk raporu
├── MYBRAIN.MD           # Kişisel bellek (strategy, telos, progress, chathistory)
├── MYPPDFS.MD           # Branş notları (Pato, Endo, Radyo, Protez vb.)
├── requirements.txt     # Python bağımlılıkları (Torch, Sentence-Transformers dahil)
├── dus_jsonlari/        # 2015-2026 arası standardize edilmiş sınav JSON'ları
├── scripts/             # Aktif Python motorları ve senkronizasyon araçları
├── vektörlenecek/       # Yeni vektörlenecek dosyalar için staging alanı
└── archive/             # Legacy kod ve bot arşivi
```

---

## 4. Aktif Python Scriptleri (scripts/)

-   **`auto_sync_dus.py`**: Günlük senkronizasyon orkestratörüdür. TELOS, DUS notları ve sohbet geçmişini Pinecone'a aktarır.
-   **`dus_uploader.py`**: Manifest tabanlı delta-sync motorudur. SHA256 kontrolü yaparak yalnızca değişen dosyaları yükler.
-   **`search_engine.py`**: Ana arama motorudur. Yerel embedding kullanarak Pinecone ve Supabase aramalarını yönetir.
-   **`embedding_utils.py`**: Yerel `multilingual-e5-large` için singleton nesneler ve vektörleme sınıfları sağlar.
-   **`cikmis_ekle.py`**: Yeni DUS sınavlarını sisteme ekleme, parse etme ve audit aracıdır.
-   **`download_model.py`**: Yerel embedding modelini indirme ve doğrulama aracıdır.
-   **`reset_brain.py`**: Bakım amaçlı `mybrain` namespace'lerini temizleme betiğidir.
-   **`daily_sync.bat`**: Windows Task Scheduler wrapper betiğidir.

---

## 5. Dokümantasyon Dosyaları

-   **`Gemini.MD`**: En üst düzey "Anayasa" belgesidir. Ajanın uyması gereken kesin kuralları içerir.
-   **`EMBEDDING.MD`**: Yerel-öncelikli vektörleme ve reranker entegrasyonu rehberi.
-   **`MYBRAIN.MD`**: Kişisel bilgi hiyerarşisi (telos, progress, memory) protokolü.
-   **`MYPPDFS.MD`**: Tüm branşların (Endodonti, Radyoloji, Patoloji vb.) indeks organizasyonu.
-   **`CIKMIS_SORULAR.MD`**: 12 yıllık DUS çıkmış soru havuzunun standardizasyon rehberi.
-   **`DUSBANKASI.MD`**: Supabase/Pinecone tabanlı soru bankası katmanı.

---

## 6. İş Akışları (Workflows)
-   **`/ders-calis`**: S5 Pipeline tabanlı konu anlatımı ve özgün soru üretimi.
-   **`/cikmis`**: Kavram bazlı çıkmış soru frekans analizi ve analitik sorgulama.
-   **`/soru-uret`**: Branş ve konu bazlı özgün DUS tarzı soru seti üretimi.
-   **`/karsilastir`**: İki hastalık veya kavramın diferansiyel matris analizi.
-   **`/cikmis-ekle`**: Yeni sınav PDF'lerini sisteme dahil etme süreci.
-   **`/hafiza-kaydet`**: Oturum notlarını kalıcı belleğe (Pinecone) mühürleme.
-   **`/debug`**: Sistem hatalarını ve veri tutarsızlıklarını giderme.

---
*Bu README, LLM'lerin projeyi saniyeler içinde anlayabilmesi için yapılandırılmıştır.*
