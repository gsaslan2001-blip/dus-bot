"""
anki_dedup.py — Pinecone `anki` indeksinde benzerlik analizi
Namespace içindeki kartları iterate eder, her kart için top-10 komşu sorgular.
Benzerlik >= 0.90 olan çiftleri JSON raporu olarak yazar.
Çapraz format karşılaştırması: Cloze ↔ Basic kartlar da kıyaslanır.

Kullanım:
    python scripts/anki_dedup.py --ns protez
    python scripts/anki_dedup.py --ns radyoloji --threshold 0.88
    python scripts/anki_dedup.py --ns protez --top-k 15
"""

import os
import sys
import json
import time
import argparse
import codecs
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

from dotenv import load_dotenv

# --- Init ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from embedding_utils import get_local_embedder
except ImportError:
    logger.error("embedding_utils bulunamadı.")
    sys.exit(1)

from pinecone import Pinecone

# --- Config ---
ANKI_HOST = os.environ.get("ANKI_HOST", "anki-0crkhvy.svc.aped-4627-b74a.pinecone.io")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
ANKI_JSONLAR = PROJECT_DIR / "anki_jsonlar"
DEFAULT_THRESHOLD = 0.90
DEFAULT_TOP_K = 10
QUERY_DELAY = 0.05  # saniye — rate limit koruması

if not PINECONE_API_KEY:
    logger.error("PINECONE_API_KEY .env'de tanımlı değil.")
    sys.exit(1)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=ANKI_HOST)


def load_cards_from_json(namespace: str) -> List[dict]:
    """
    anki_jsonlar/ dizininde namespace'e ait JSON dosyaları arar.
    namespace = ders (örn: protez). Birden fazla dosya olabilir.
    """
    cards = []
    json_files = sorted(ANKI_JSONLAR.glob(f"{namespace}_*.json"))
    # Dedup rapor dosyalarını hariç tut
    json_files = [f for f in json_files if not f.name.endswith("_dedup_report.json")]

    if not json_files:
        logger.error(f"Namespace '{namespace}' için JSON bulunamadı: {ANKI_JSONLAR}/{namespace}_*.json")
        sys.exit(1)

    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            batch = json.load(f)
        cards.extend(batch)
        logger.info(f"Yüklendi: {jf.name} ({len(batch)} kart)")

    logger.info(f"Toplam {len(cards)} kart yüklendi (namespace={namespace})")
    return cards


def query_similar(vec: List[float], namespace: str, top_k: int, exclude_id: str) -> List[dict]:
    """
    Pinecone'a ham vektör ile sorgu yapar.
    Kendisini (exclude_id) sonuçlardan çıkarır.
    """
    try:
        result = index.query(
            vector=vec,
            top_k=top_k + 1,  # +1: kendisi de dönebilir
            namespace=namespace,
            include_metadata=True,
        )
    except Exception as e:
        logger.warning(f"Sorgu hatası (guid={exclude_id}): {e}")
        return []

    matches = []
    for m in result.get("matches", []):
        if m["id"] == exclude_id:
            continue  # Kendisini atla
        matches.append({
            "id": m["id"],
            "score": round(m["score"], 4),
            "metadata": m.get("metadata", {}),
        })
    return matches


def find_duplicates(
    cards: List[dict],
    namespace: str,
    threshold: float,
    top_k: int,
) -> List[Dict[str, Any]]:
    """
    Tüm kartları iterate eder, benzerlik >= threshold olan çiftleri bulur.
    Her çift yalnızca bir kez raporlanır (A-B = B-A tekrarı engellenir).
    """
    embedder = get_local_embedder()
    seen_pairs: Set[Tuple[str, str]] = set()
    duplicate_pairs = []

    total = len(cards)
    logger.info(f"Benzerlik analizi başlıyor: {total} kart, threshold={threshold}")

    for idx, card in enumerate(cards, start=1):
        guid = card.get("guid", "")
        if not guid:
            continue

        vmetin = card.get("vektorlenecek_metin", "")
        if not vmetin:
            continue

        if idx % 20 == 0 or idx == 1 or idx == total:
            logger.info(f"  [{idx}/{total}] {guid[:12]}...")

        # Yerel E5 ile embed et (query mode) — embed_text prefix'i kendi ekler
        vec = embedder.embed_text(vmetin, is_query=True)

        # Pinecone'a sor
        similar = query_similar(vec, namespace, top_k, guid)
        time.sleep(QUERY_DELAY)

        for match in similar:
            score = match["score"]
            if score < threshold:
                continue

            match_guid = match["id"]
            pair_key = tuple(sorted([guid, match_guid]))
            if pair_key in seen_pairs:
                continue  # Zaten raporlandı
            seen_pairs.add(pair_key)

            meta_b = match["metadata"]
            duplicate_pairs.append({
                "score": score,
                "kart_a_guid": guid,
                "kart_b_guid": match_guid,
                "kart_a_tipi": card.get("kart_tipi", "?"),
                "kart_b_tipi": meta_b.get("kart_tipi", "?"),
                "kart_a_baslik": card.get("baslik", ""),
                "kart_b_baslik": meta_b.get("baslik", ""),
                "kart_a_metin": vmetin,
                "kart_b_metin": meta_b.get("text", ""),
            })

    # Score'a göre sırala (en yüksek önce)
    duplicate_pairs.sort(key=lambda x: x["score"], reverse=True)
    return duplicate_pairs


def save_report(pairs: List[Dict[str, Any]], namespace: str, threshold: float) -> Path:
    """Raporu JSON ve okunabilir TXT formatında kaydeder."""
    ANKI_JSONLAR.mkdir(parents=True, exist_ok=True)

    # JSON raporu
    json_path = ANKI_JSONLAR / f"{namespace}_dedup_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON raporu: {json_path}")

    # Okunabilir TXT raporu
    txt_path = ANKI_JSONLAR / f"{namespace}_dedup_report.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# Benzerlik Raporu — Namespace: {namespace}\n")
        f.write(f"# Eşik: {threshold} | Toplam çift: {len(pairs)}\n")
        f.write("=" * 80 + "\n\n")

        for i, pair in enumerate(pairs, start=1):
            f.write(f"[{i}] SCORE: {pair['score']:.4f}\n")
            f.write(f"  KART A ({pair['kart_a_tipi']}) | GUID: {pair['kart_a_guid']}\n")
            f.write(f"  Başlık: {pair['kart_a_baslik']}\n")
            f.write(f"  Metin : {pair['kart_a_metin'][:200]}\n")
            f.write(f"\n  KART B ({pair['kart_b_tipi']}) | GUID: {pair['kart_b_guid']}\n")
            f.write(f"  Başlık: {pair['kart_b_baslik']}\n")
            f.write(f"  Metin : {pair['kart_b_metin'][:200]}\n")
            f.write("\n" + "-" * 80 + "\n\n")

    logger.info(f"TXT raporu: {txt_path}")
    return json_path


def main():
    # Windows UTF-8 fix
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Anki kartları benzerlik analizi — duplikat tespiti",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/anki_dedup.py --ns protez
  python scripts/anki_dedup.py --ns radyoloji --threshold 0.88
  python scripts/anki_dedup.py --ns protez --top-k 15
        """
    )
    parser.add_argument("--ns", type=str, required=True, help="Analiz edilecek namespace (örn: protez)")
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"Benzerlik eşiği (varsayılan: {DEFAULT_THRESHOLD})"
    )
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help=f"Her kart için kaç komşu sorgulanacak (varsayılan: {DEFAULT_TOP_K})"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Namespace içindeki tüm dosyalar yerine sadece belirtilen JSON dosyasını analiz et"
    )
    args = parser.parse_args()

    namespace = args.ns.lower().strip()
    threshold = args.threshold
    top_k = args.top_k
    file_arg = args.file

    if not 0.0 < threshold < 1.0:
        logger.error(f"Geçersiz threshold: {threshold}. 0 ile 1 arasında olmalı.")
        sys.exit(1)

    # Kartları local JSON'dan yükle
    if file_arg:
        file_path = Path(file_arg)
        if not file_path.exists():
            logger.error(f"Belirtilen dosya bulunamadı: {file_path}")
            sys.exit(1)
        with open(file_path, encoding="utf-8") as f:
            cards = json.load(f)
        logger.info(f"Yalnızca belirtilen dosya yüklendi: {file_path.name} ({len(cards)} kart)")
    else:
        cards = load_cards_from_json(namespace)

    # Benzerlik analizi yap
    pairs = find_duplicates(cards, namespace, threshold, top_k)

    # Raporu kaydet
    if pairs:
        report_path = save_report(pairs, namespace, threshold)
        print(f"\n✅ {len(pairs)} benzer çift bulundu.")
        print(f"📄 JSON: {ANKI_JSONLAR / (namespace + '_dedup_report.json')}")
        print(f"📄 TXT : {ANKI_JSONLAR / (namespace + '_dedup_report.txt')}")
        print(f"\nSilinecek GUID'leri seç → to_delete.txt oluştur → anki_delete.py çalıştır")
    else:
        print(f"\n✅ {namespace} namespace'inde threshold={threshold} üzerinde benzer kart bulunamadı.")


if __name__ == "__main__":
    main()
