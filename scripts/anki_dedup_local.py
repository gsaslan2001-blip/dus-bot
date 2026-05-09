"""
anki_dedup_local.py — Yerel Anki JSON Dosyası İçi Benzerlik Analizi
Namespace/Dosya içindeki kartları kendi arasında kıyaslar. Pinecone'a yüklemez.

Kullanım:
    python scripts/anki_dedup_local.py --ders fizyo --unite basic
    python scripts/anki_dedup_local.py --ders fizyo --unite basic --threshold 0.85
"""

import os
import sys
import json
import argparse
import codecs
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Windows UTF-8 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    except Exception:
        pass

# --- Paths ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from embedding_utils import get_embedder
except ImportError:
    print("embedding_utils bulunamadı.")
    sys.exit(1)

import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Yerel Anki JSON Dosyası İçi Benzerlik Analizi")
    parser.add_argument("--ders", type=str, required=True, help="Ders adı (örn: fizyo)")
    parser.add_argument("--unite", type=str, required=True, help="Ünite adı (örn: basic)")
    parser.add_argument("--threshold", type=float, default=0.84, help="Eşitlik eşiği (varsayılan: 0.84)")
    parser.add_argument("--threads", type=int, default=4, help="PyTorch CPU thread sayısı")
    parser.add_argument("--batch-size", type=int, default=16, help="Encoding batch size")
    args = parser.parse_args()

    # PyTorch CPU thread sayısını sınırla/optimize et
    torch.set_num_threads(args.threads)
    logger.info(f"PyTorch threads set to: {args.threads}")

    ANKI_JSONLAR = PROJECT_DIR / "anki_jsonlar"
    json_path = ANKI_JSONLAR / f"{args.ders}_{args.unite}.json"

    if not json_path.exists():
        logger.error(f"Dosya bulunamadı: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        cards = json.load(f)

    logger.info(f"{len(cards)} kart yüklendi. Vektörleme başlıyor...")
    embedder = get_embedder("openai")

    texts = [c.get("vektorlenecek_metin", "") for c in cards]
    prefixed = [f"passage: {t}" if not t.startswith("passage: ") else t for t in texts]

    # embed_batch yerine doğrudan optimize encode çağrısı
    logger.info(f"Encoding {len(texts)} texts...")
    start_time = time.time()
    
    # Model encode çağrısı
    vectors = embedder.embed_batch(prefixed)
    
    elapsed = time.time() - start_time
    logger.info(f"Vektörleme tamamlandı ({elapsed:.2f} saniye). Benzerlikler hesaplanıyor...")
    
    # torch ile benzerlik matrisi (dot product = cosine sim for normalized vectors)
    vec_tensor = torch.tensor(vectors, dtype=torch.float32)
    sim_matrix = torch.mm(vec_tensor, vec_tensor.t())

    duplicate_pairs = []
    seen_pairs = set()

    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            score = sim_matrix[i, j].item()
            if score >= args.threshold:
                guid_a = cards[i]["guid"]
                guid_b = cards[j]["guid"]
                pair_key = tuple(sorted([guid_a, guid_b]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                duplicate_pairs.append({
                    "score": round(score, 4),
                    "kart_a_guid": guid_a,
                    "kart_b_guid": guid_b,
                    "kart_a_tipi": cards[i].get("kart_tipi", "?"),
                    "kart_b_tipi": cards[j].get("kart_tipi", "?"),
                    "kart_a_baslik": cards[i].get("baslik", ""),
                    "kart_b_baslik": cards[j].get("baslik", ""),
                    "kart_a_metin": cards[i].get("vektorlenecek_metin", ""),
                    "kart_b_metin": cards[j].get("vektorlenecek_metin", ""),
                })

    duplicate_pairs.sort(key=lambda x: x["score"], reverse=True)
    
    # Raporları kaydet
    report_json = ANKI_JSONLAR / f"{args.ders}_{args.unite}_internal_dedup_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(duplicate_pairs, f, ensure_ascii=False, indent=2)

    report_txt = ANKI_JSONLAR / f"{args.ders}_{args.unite}_internal_dedup_report.txt"
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write(f"# Dahili Benzerlik Raporu\n")
        f.write(f"# Dosya: {args.ders}_{args.unite}.json\n")
        f.write(f"# Eşik: {args.threshold} | Toplam Çift: {len(duplicate_pairs)}\n")
        f.write("=" * 80 + "\n\n")

        for idx, pair in enumerate(duplicate_pairs, start=1):
            f.write(f"[{idx}] SCORE: {pair['score']:.4f}\n")
            f.write(f"  KART A ({pair['kart_a_tipi']}) | GUID: {pair['kart_a_guid']}\n")
            f.write(f"  Başlık: {pair['kart_a_baslik']}\n")
            f.write(f"  Metin : {pair['kart_a_metin']}\n\n")
            f.write(f"  KART B ({pair['kart_b_tipi']}) | GUID: {pair['kart_b_guid']}\n")
            f.write(f"  Başlık: {pair['kart_b_baslik']}\n")
            f.write(f"  Metin : {pair['kart_b_metin']}\n")
            f.write("-" * 80 + "\n\n")

    logger.info(f"Analiz bitti. {len(duplicate_pairs)} kopya çift bulundu.")
    print(f"\n✅ Raporlar oluşturuldu:")
    print(f"   - JSON: {report_json}")
    print(f"   - TXT:  {report_txt}")

if __name__ == "__main__":
    main()

