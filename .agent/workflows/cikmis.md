# 🎯 Çıkmış Soru Analiz Protokolü (DUS Mentörü)
> Son güncelleme: 2026-04-27 | v1.1 — Kesin Kısalmama ve Tam Kaynak Bağlılığı Kuralları Eklendi.

> **⚠️ KRİTİK TALİMAT:** Bu protokol uygulanırken kullanıcı isteği veya kaynak verisi **ASLA** özetlenemez, kısaltılamaz veya "temsili" hale getirilemez. Kaynaklarda (`myppdfs`) bulunan her türlü ilgili veri ve `cikmis` namespace'indeki **TÜM** eşleşen sorular eksiksiz sunulmalıdır. "Cevapları seçme" veya "özetleme" davranışı sistem hatası kabul edilir.

---

## ── ADIM 1: KAYNAK TARAMA VE KAVRAM ÖZÜTLEME ──────────────────

- **Sorgu:** Kullanıcının verdiği konu başlığı için `myppdfs` indeksindeki ilgili branş namespace'lerinde arama yap.
- **Analiz:** Gelen kaynak metinlerinden şunları çıkar (Kısaltmadan, tüm detaylarıyla):
    1.  **High-Yield Kavramlar:** Konunun "olmazsa olmaz" anahtar terimleri.
    2.  **Alt Başlıklar:** Konunun akademik hiyerarşisi.
    3.  **Kavram Listesi:** Çıkmış sorularda aranacak olan tüm teknik terimlerin listesi.

---

## ── ADIM 2: DUS ÇIKMIŞ SORU KORELASYONU ───────────────────────

- **Sorgu:** Adım 1'de çıkarılan **Kavram Listesi**'ndeki her bir terimi `myppdfs/cikmis` namespace'inde ara.
- **Nicel Rapor:** Her bir kavramın geçmiş sorularda **toplam kaç kez** yer aldığını liste olarak sun.
- **Soru Sunumu:** Eşleşen **TÜM** soruları (hiçbirini elemeden) aşağıdaki formatta tam metin olarak sun:
    - **Soru Metni** (Orijinal haliyle)
    - **Tüm Şıklar (A, B, C, D, E)**
    - *Format: Standart Markdown*

---

## ── ADIM 3: KAYNAK TABANLI CEVAP ANAHTARI ─────────────────────

- **Sentez:** Sunulan soruların cevaplarını SADECE elimizdeki akademik kaynaklardaki (`myppdfs`) bilgilerle doğrula.
- **Kısıtlama:** Dışarıdan bilgi ekleme, kaynakta olmayan gerekçe üretme.
- **Format:** Dosyanın en sonunda "Cevap Anahtarı ve Kaynak Referansı" başlığı altında sun.
    - Soru No - Doğru Şık - Kaynak Gerekçesi (Tam metin/mekanizma).

---

## ── ADIM 4: HAFIZA KAYDI ─────────────────────────────────────

- **Kayıt:** Bu analiz raporunu `vektörlenecek/cikmis_analiz_[konu].md` olarak kaydet.
- **Vektörleme:** Pinecone `mybrain/chathistory` namespace'ine aktar.

---

## ── KESİN KISITLAMALAR ──────────────────────────────────────

1.  **Sıfır Özet:** Kullanıcının veya kaynağın verisini özetlemek yasaktır.
2.  **Sıfır Filtre:** "Benzer" veya "temsili" diyerek soru elemek yasaktır. 50 soru çıksa bile 50'si de verilir.
3.  **Tam Sadakat:** Sadece kaynaklardaki terminoloji kullanılır.

---
*Çıkmış Soru Analiz Protokolü v1.1 | DUS Mentörü Projesi | 2026-04-27*
