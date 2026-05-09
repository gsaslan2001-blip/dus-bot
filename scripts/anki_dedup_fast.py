"""
anki_dedup_fast.py — Hızlı Token Tabanlı Anki Kartı Benzerlik Analizi
DUSBANKASI'ndaki token temizleme ve overlap/Jaccard mantığını vektör gerektirmeden çalıştırır.
"""

import os
import sys
import re
import json
import codecs
import logging
from pathlib import Path
from itertools import combinations

# Windows UTF-8 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_TR_STOPWORDS = {
    "bir", "ve", "ile", "bu", "da", "de", "ki", "için", "olan", "bu", "şu", "o", "ne", "en", "daha", "çok", "az", "gibi",
    "kadar", "sonra", "önce", "göre", "biri", "her", "hiç", "hem", "ya",
    "veya", "ama", "fakat", "ancak", "değil", "mi", "mı", "mu", "mü",
    "var", "yok", "ise", "iken", "tarafından",
    "üzerinde", "altında", "içinde", "dışında", "arasında", "hangi",
    "nasıl", "neden", "nerede", "kim", "kimin", "buna", "bunu", "bunda",
    "bunun", "bunlar", "şuna", "şunu", "ona", "onu", "bunları", "şunları",
    "onları", "aşağıdaki", "aşağıda", "yukarıdaki", "hangisi", "birinde",
    "birini", "birinin", "hepsi", "tüm", "tamamı",
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", 
}

_TR_STOPWORDS_EK = {
    "olur", "olmuş", "olmaz", "oluşur", "oluşan", "oluşmaz",
    "edilir", "edilmiş", "edilmez", "edilmektedir", "edilmelidir",
    "yapılır", "yapılmış", "yapılmaz", "yapılmaktadır", "yapılmalıdır",
    "görülür", "görülmüş", "görülmez", "görülmektedir",
    "alınır", "verilir", "geçer", "gider", "gelir",
    "alınmaktadır", "verilmektedir", "geçmektedir", "tutulmaktadır", "taşımaktadır", "sürmektedir",
    "kabul", "tanımlanır", "bilinir", "sayılır", "ifade", "belirtilen", "vurgulanan",
    "yardır", "izlenir", "saptanır", "tespit",
    "meydana", "gelir", "ortaya", "çıkar", "yer", "alır", "söz", "konusudur",
    "bilinmektedir", "düşünülmektedir", "belirtilmektedir", "vurgulanmaktedir", 
    "öngörülmektedir", "gerektirir", "sağlar", "içerir", "olmaktadır", "olunmaktadır",
    "artık", "hâlâ", "henüz", "zaten", "çoktan", "yalnızca", "sadece", "yani", "işte",
    "aslında", "esasen", "özünde", "temelde", "itibaren", "başlayarak", "süresince", 
    "sırasında", "sürecinde", "esnasında", "boyunca", "oldukça", "epey", "hayli", "pek", 
    "son", "derece", "fazlasıyla", "gayet", "nispeten", "görece", "kısmen", "tamamen", 
    "tümüyle", "büsbütün", "kesinlikle", "mutlaka", "zorunlu", "ağırlıklı", "büyük", "ölçüde",
    "ne", "var", "ki", "buna", "karşın", "rağmen", "öte", "yandan", 
    "yanında", "yanı", "sıra", "ek", "açıdan", "bağlamda", 
    "doğrultuda", "şekilde", "biçimde", "ancak", "çünkü", "dolayısıyla",
    "sonucu", "sonucunda", "nedeniyle", "yoluyla", "olup", "olmak",
    "temel", "ana", "asıl", "esas", "başlıca", "önemli", "kritik", "ciddi", 
    "belirgin", "belirli", "spesifik", "ilgili", "uygun", "bazı", "birkaç", 
    "birçok", "çeşitli", "az", "sayıda", "çoğunluğu", "bir", "kısmı", "bölümü", "diğer",
    "nasıldır", "düşük", "yüksek", "eşit", "hangisidir", "nedir", "nerede", 
    "tanımlayın", "sayın", "lokalizedir", "lokalize", "yoğunluk", "değeri", 
    "etkeni", "rolünü", "açıklayın", "faktöre", "bağlıdır", "sayın", "kandakine",
    "sebebi", "oranı", "yaklaşık", "durumundaki", "sıralayın", "kandaki"
}

_ALL_STOPWORDS = _TR_STOPWORDS | _TR_STOPWORDS_EK

def _tokenize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', ' ', text)
    tokens = set(text.split())
    return tokens - _ALL_STOPWORDS

def asymmetric_similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def parse_anki_txt(file_path: Path):
    cards = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                guid = parts[0].strip('"')
                question = parts[3].strip('"')
                answer = parts[4].strip('"') if len(parts) > 4 else ""
                tag = parts[5].strip() if len(parts) > 5 else ""
                
                cards.append({
                    "guid": guid,
                    "question": question,
                    "answer": answer,
                    "tag": tag,
                    "tokens_q": _tokenize(question),
                    "tokens_a": _tokenize(answer)
                })
    return cards

def run_analysis(file_path: Path, out_dir: Path, overlap_threshold: float, jaccard_threshold: float):
    cards = parse_anki_txt(file_path)
    logger.info(f"{len(cards)} kart yüklendi. Hızlı token kıyaslaması başlıyor...")

    duplicate_pairs = []
    total_pairs = len(cards) * (len(cards) - 1) // 2
    logger.info(f"Toplam {total_pairs:,} ikili karşılaştırma yapılacak...")

    for c1, c2 in combinations(cards, 2):
        if not c1["tokens_q"] or not c2["tokens_q"]:
            continue

        overlap_q = asymmetric_similarity(c1["tokens_q"], c2["tokens_q"])
        jaccard_q = jaccard(c1["tokens_q"], c2["tokens_q"])

        if overlap_q >= overlap_threshold or jaccard_q >= jaccard_threshold:
            duplicate_pairs.append({
                "overlap_score": round(overlap_q, 4),
                "jaccard_score": round(jaccard_q, 4),
                "kart_a_guid": c1["guid"],
                "kart_b_guid": c2["guid"],
                "kart_a_baslik": c1["tag"],
                "kart_b_baslik": c2["tag"],
                "kart_a_metin": c1["question"],
                "kart_b_metin": c2["question"],
                "tokens_a": list(c1["tokens_q"]),
                "tokens_b": list(c2["tokens_q"]),
                "common_tokens": list(c1["tokens_q"] & c2["tokens_q"])
            })

    duplicate_pairs.sort(key=lambda x: x["overlap_score"], reverse=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = file_path.stem

    report_json = out_dir / f"{stem}_fast_dedup_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(duplicate_pairs, f, ensure_ascii=False, indent=2)

    report_txt = out_dir / f"{stem}_fast_dedup_report.txt"
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write(f"# Dahili Hızlı Benzerlik Raporu (Token Bazlı)\n")
        f.write(f"# Dosya: {file_path.name}\n")
        f.write(f"# Overlap Eşik: {overlap_threshold} | Jaccard Eşik: {jaccard_threshold}\n")
        f.write(f"# Toplam Benzer Çift: {len(duplicate_pairs)}\n")
        f.write("=" * 80 + "\n\n")

        for idx, pair in enumerate(duplicate_pairs, start=1):
            f.write(f"[{idx}] OVERLAP: {pair['overlap_score']:.4f} | JACCARD: {pair['jaccard_score']:.4f}\n")
            f.write(f"  KART A | GUID: {pair['kart_a_guid']}\n")
            f.write(f"  Başlık: {pair['kart_a_baslik']}\n")
            f.write(f"  Metin : {pair['kart_a_metin']}\n")
            f.write(f"  Anahtar Kelimeler A: {pair['tokens_a']}\n\n")
            f.write(f"  KART B | GUID: {pair['kart_b_guid']}\n")
            f.write(f"  Başlık: {pair['kart_b_baslik']}\n")
            f.write(f"  Metin : {pair['kart_b_metin']}\n")
            f.write(f"  Anahtar Kelimeler B: {pair['tokens_b']}\n")
            f.write(f"  Ortak Kelimeler: {pair['common_tokens']}\n")
            f.write("-" * 80 + "\n\n")

    logger.info(f"Analiz bitti. {len(duplicate_pairs)} kopya çift bulundu.")
    print(f"\nRaporlar oluşturuldu:")
    print(f"   - JSON: {report_json}")
    print(f"   - TXT:  {report_txt}")
    return len(duplicate_pairs)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hızlı token tabanlı Anki kart benzerlik analizi")
    parser.add_argument("--txt", required=True, help="Anki .txt dosyası yolu")
    parser.add_argument("--out-dir", default=str(PROJECT_DIR / "anki_jsonlar"), help="Rapor çıktı dizini")
    parser.add_argument("--overlap-threshold", type=float, default=0.65, help="Asymmetric overlap eşiği (varsayılan: 0.65)")
    parser.add_argument("--jaccard-threshold", type=float, default=0.50, help="Jaccard eşiği (varsayılan: 0.50)")
    args = parser.parse_args()

    file_path = Path(args.txt)
    if not file_path.exists():
        logger.error(f"Dosya bulunamadı: {file_path}")
        sys.exit(1)

    run_analysis(file_path, Path(args.out_dir), args.overlap_threshold, args.jaccard_threshold)

if __name__ == "__main__":
    main()
