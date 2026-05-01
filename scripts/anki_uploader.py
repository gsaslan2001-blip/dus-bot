"""
anki_uploader.py — Anki JSON → Pinecone `anki` indeksi
GUID tabanlı manifest: sadece yeni/değişen kartları yükler.
Yerel Multilingual-E5-Large embedding kullanır (bulut embedding YASAK).

Kullanım:
    python scripts/anki_uploader.py --json anki_jsonlar/protez_dis_morfolojisi.json --ns protez
    python scripts/anki_uploader.py --all   # anki_jsonlar/ altındaki tüm JSON'ları yükler
"""

import os
import sys
import json
import time
import hashlib
import argparse
import codecs
import logging
import functools
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# --- Init ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

# Local modules
try:
    from embedding_utils import get_local_embedder
except ImportError:
    logger.error("embedding_utils bulunamadı. scripts/ dizininde mi?")
    sys.exit(1)

from pinecone import Pinecone

# --- Config ---
ANKI_HOST = os.environ.get("ANKI_HOST", "anki-0crkhvy.svc.aped-4627-b74a.pinecone.io")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
ANKI_JSONLAR = PROJECT_DIR / "anki_jsonlar"
MANIFEST_PATH = SCRIPT_DIR / "anki_manifest.json"
BATCH_SIZE = 50

# --- Pinecone client ---
if not PINECONE_API_KEY:
    logger.error("PINECONE_API_KEY .env'de tanımlı değil.")
    sys.exit(1)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=ANKI_HOST)


# --- Retry decorator ---
def retry_operation(retries: int = 3, delay: float = 2.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"[{func.__name__}] Hata (deneme {attempt+1}/{retries}): {e}")
                    if attempt < retries - 1:
                        time.sleep(delay * (attempt + 1))
                    else:
                        logger.error(f"[{func.__name__}] Tüm denemeler başarısız.")
                        raise
        return wrapper
    return decorator


# --- Manifest ---
def load_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: Dict[str, Any]):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def card_hash(card: dict) -> str:
    """Kartın içeriğinden deterministic hash üretir (değişiklik tespiti için)."""
    key = card.get("vektorlenecek_metin", "") + card.get("kart_tipi", "")
    return hashlib.md5(key.encode("utf-8")).hexdigest()


# --- Pinecone ops ---
@retry_operation(retries=3, delay=2.0)
def upsert_batch(vectors: List[Dict[str, Any]], namespace: str):
    index.upsert(vectors=vectors, namespace=namespace)


@retry_operation(retries=3, delay=2.0)
def delete_ids_from_pinecone(ids: List[str], namespace: str):
    index.delete(ids=ids, namespace=namespace)


# --- Build vector record ---
def build_vector(card: dict, vec: List[float]) -> Dict[str, Any]:
    """Pinecone'a yüklenecek vektör kaydını oluşturur."""
    metadata = {
        "text": card["vektorlenecek_metin"],
        "guid": card["guid"],
        "ders": card["ders"],
        "unite": card["unite"],
        "kart_tipi": card["kart_tipi"],
        "baslik": card.get("baslik", ""),
        "text_clean": card.get("text_clean", ""),
    }
    # kart tipine özgü metadata
    if card["kart_tipi"] == "cloze":
        metadata["extra"] = card.get("extra", "")
    else:
        metadata["front"] = card.get("front", "")
        metadata["back"] = card.get("back", "")

    return {
        "id": card["guid"],
        "values": vec,
        "metadata": metadata,
    }


# --- Upload logic ---
def upload_json(json_path: Path, namespace: str, force: bool = False, dry_run: bool = False) -> int:
    """
    Tek JSON dosyasını Pinecone'a yükler.
    Manifest kontrolü ile sadece yeni/değişen kartları işler.
    Returns: yüklenen kart sayısı
    """
    logger.info(f"[{namespace}] Okunuyor: {json_path.name}")

    with open(json_path, encoding="utf-8") as f:
        cards: List[dict] = json.load(f)

    if not cards:
        logger.warning(f"[{namespace}] JSON boş: {json_path.name}")
        return 0

    manifest = load_manifest()

    # Hangi kartlar yeni veya değişmiş?
    to_upload = []
    for card in cards:
        guid = card.get("guid", "")
        if not guid:
            logger.warning(f"GUID eksik, atlanıyor: {card}")
            continue

        h = card_hash(card)
        manifest_key = f"{namespace}::{guid}"

        if not force and manifest.get(manifest_key, {}).get("hash") == h:
            continue  # Değişmemiş, atla

        to_upload.append((card, h, manifest_key))

    if not to_upload:
        logger.info(f"[{namespace}] Değişen kart yok, yükleme atlandı.")
        return 0

    logger.info(f"[{namespace}] {len(to_upload)} kart yüklenecek (toplam: {len(cards)})")

    if dry_run:
        logger.info(f"[DRY-RUN] {len(to_upload)} kart yüklenirdi.")
        return len(to_upload)

    # Embed et (batch)
    embedder = get_local_embedder()
    texts = [card["vektorlenecek_metin"] for card, _, _ in to_upload]

    logger.info(f"[{namespace}] Embedding başlıyor ({len(texts)} kart)...")
    vectors_raw = embedder.embed_batch(texts, is_query=False)
    logger.info(f"[{namespace}] Embedding tamamlandı.")

    # Batch upsert
    vector_records = []
    for (card, h, manifest_key), vec in zip(to_upload, vectors_raw):
        vector_records.append(build_vector(card, vec))

    uploaded = 0
    for i in range(0, len(vector_records), BATCH_SIZE):
        batch = vector_records[i : i + BATCH_SIZE]
        upsert_batch(batch, namespace)
        uploaded += len(batch)
        logger.info(f"[{namespace}] Upsert: {uploaded}/{len(vector_records)}")

    # Manifest güncelle
    for card, h, manifest_key in to_upload:
        manifest[manifest_key] = {
            "hash": h,
            "namespace": namespace,
            "ders": card["ders"],
            "unite": card["unite"],
        }
    save_manifest(manifest)

    logger.info(f"[{namespace}] ✅ {uploaded} kart yüklendi.")
    return uploaded


def delete_card(guid: str, namespace: str):
    """Tek kartı Pinecone'dan sil ve manifestten kaldır."""
    delete_ids_from_pinecone([guid], namespace)
    manifest = load_manifest()
    manifest_key = f"{namespace}::{guid}"
    if manifest_key in manifest:
        del manifest[manifest_key]
        save_manifest(manifest)
    logger.info(f"[{namespace}] Silindi: {guid}")


# --- Main ---
def main():
    # Windows UTF-8 fix
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Anki JSON → Pinecone `anki` yükleyici",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/anki_uploader.py --json anki_jsonlar/protez_dis_morfolojisi.json --ns protez
  python scripts/anki_uploader.py --all
  python scripts/anki_uploader.py --json anki_jsonlar/radyoloji_radyoloji_fizigi.json --ns radyoloji --force
        """
    )
    parser.add_argument("--json", type=str, default=None, help="Yüklenecek JSON dosyası")
    parser.add_argument("--ns", type=str, default=None, help="Hedef namespace (örn: protez)")
    parser.add_argument("--all", action="store_true", help="anki_jsonlar/ altındaki tüm JSON'ları yükle")
    parser.add_argument("--force", action="store_true", help="Manifest görmezden gel, hepsini yeniden yükle")
    parser.add_argument("--dry-run", action="store_true", help="Yükleme yapma, sadece say")
    args = parser.parse_args()

    if not args.json and not args.all:
        parser.error("--json ya da --all gerekli.")

    total = 0

    if args.all:
        if not ANKI_JSONLAR.exists():
            logger.error(f"anki_jsonlar/ dizini bulunamadı: {ANKI_JSONLAR}")
            sys.exit(1)
        json_files = sorted(ANKI_JSONLAR.glob("*.json"))
        # dedup rapor dosyalarını atla
        json_files = [f for f in json_files if not f.name.endswith("_dedup_report.json")]
        if not json_files:
            logger.warning("anki_jsonlar/ dizininde JSON dosyası bulunamadı.")
            sys.exit(0)

        for jf in json_files:
            # Dosya adından namespace çıkar: protez_dis_morfolojisi.json → protez
            ns = jf.stem.split("_")[0]
            total += upload_json(jf, ns, force=args.force, dry_run=args.dry_run)
    else:
        json_path = Path(args.json)
        if not json_path.exists():
            logger.error(f"JSON bulunamadı: {json_path}")
            sys.exit(1)
        if not args.ns:
            parser.error("--json kullanırken --ns de gereklidir.")
        total += upload_json(json_path, args.ns, force=args.force, dry_run=args.dry_run)

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{prefix}✅ Toplam {total} kart yüklendi.")


if __name__ == "__main__":
    main()
