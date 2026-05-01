"""
anki_delete.py — AnkiConnect + Pinecone silme scripti
Silmek istediğin GUID listesini alır:
  1. AnkiConnect (localhost:8765) üzerinden Anki'den notu siler
  2. Pinecone `anki` indeksinden vektörü kaldırır
  3. anki_manifest.json'u günceller

GUID nereden gelir: anki_dedup.py çıktısındaki raporu inceleyip
  silineceklerin GUID'lerini to_delete.txt dosyasına yaz (her satır bir GUID).

Kullanım:
    python scripts/anki_delete.py --file to_delete.txt --ns protez
    python scripts/anki_delete.py --guids "z!Zx)KuOg6" "B-OVGzEaX1" --ns radyoloji
    python scripts/anki_delete.py --file to_delete.txt --ns protez --dry-run
    python scripts/anki_delete.py --file to_delete.txt --ns protez --pinecone-only
    python scripts/anki_delete.py --file to_delete.txt --ns protez --anki-only
"""

import os
import sys
import json
import time
import argparse
import codecs
import logging
import requests
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# --- Init ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from pinecone import Pinecone

# --- Config ---
ANKI_HOST = os.environ.get("ANKI_HOST", "anki-0crkhvy.svc.aped-4627-b74a.pinecone.io")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
ANKICONNECT_URL = os.environ.get("ANKICONNECT_URL", "http://localhost:8765")
MANIFEST_PATH = SCRIPT_DIR / "anki_manifest.json"
BATCH_SIZE = 100

if not PINECONE_API_KEY:
    logger.error("PINECONE_API_KEY .env'de tanımlı değil.")
    sys.exit(1)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=ANKI_HOST)


# ─── AnkiConnect Helpers ───────────────────────────────────────────────────────

def anki_request(action: str, **params) -> dict:
    """AnkiConnect'e istek gönderir. Hata durumunda exception fırlatır."""
    payload = {"action": action, "version": 6, "params": params}
    try:
        resp = requests.post(ANKICONNECT_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"AnkiConnect'e bağlanılamadı ({ANKICONNECT_URL}). "
            "Anki açık mı? AnkiConnect eklentisi yüklü mü?"
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"AnkiConnect isteği başarısız: {e}")

    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"AnkiConnect hatası [{action}]: {data['error']}")
    return data.get("result")


def check_ankiconnect() -> bool:
    """AnkiConnect erişilebilir mi kontrol eder."""
    try:
        anki_request("version")
        return True
    except Exception as e:
        logger.warning(f"AnkiConnect erişilemiyor: {e}")
        return False


def guid_to_note_id(guid: str) -> Optional[int]:
    """
    Anki GUID'ini noteId'ye çevirir.
    Strateji: findNotes ile arama yap, sonra notesInfo ile GUID doğrula.
    """
    # Anki'de GUID'e göre direkt arama yapmak mümkün değil.
    # notesInfo API'si noteId alır, GUID ile arama yapamaz.
    # findNotes ile genel arama yapıp notesInfo ile GUID eşleştirme:
    try:
        # Önce "tüm notlar" arayıp GUID karşılaştırması yapıyoruz.
        # Bu yaklaşım büyük destelerde yavaş olabilir.
        # Daha iyi: notesInfo ile toplu sorgulama.

        # Tüm note ID'lerini al (note:* ile tüm desteleri tara)
        note_ids = anki_request("findNotes", query="deck:*")
        if not note_ids:
            return None

        # Batch halinde notesInfo çağır (GUID alanı içerir)
        chunk_size = 500
        for i in range(0, len(note_ids), chunk_size):
            chunk = note_ids[i : i + chunk_size]
            notes_info = anki_request("notesInfo", notes=chunk)
            for note in notes_info:
                # Anki'nin GUID alanı 'fields' içinde değil, doğrudan 'noteId' ile eşleşir.
                # AnkiConnect notesInfo'da 'fields' döndürür ama GUID'i 'guid' alanında göstermez.
                # Alternatif: Export'tan aldığımız GUID ile Anki'deki note arasında
                # 'fields' değerlerini karşılaştırmak yerine, GUID'i Anki'nin
                # internal noteId'si olarak kabul etmek mümkün değil (farklı şeyler).
                # Doğru yaklaşım: notesInfo'dan gelen 'guid' alanını kullan.
                if note.get("guid") == guid:
                    return note["noteId"]

        return None

    except Exception as e:
        logger.warning(f"GUID→noteId çevirme hatası ({guid}): {e}")
        return None


def delete_from_anki(guids: List[str], dry_run: bool = False) -> dict:
    """
    GUID listesini Anki'den siler.
    Returns: {"deleted": [guid...], "not_found": [guid...], "errors": [guid...]}
    """
    result = {"deleted": [], "not_found": [], "errors": []}

    logger.info(f"AnkiConnect: {len(guids)} GUID için noteId aranıyor...")

    guid_to_nid = {}
    for guid in guids:
        nid = guid_to_note_id(guid)
        if nid is not None:
            guid_to_nid[guid] = nid
            logger.debug(f"  {guid} → noteId={nid}")
        else:
            logger.warning(f"  GUID bulunamadı Anki'de: {guid}")
            result["not_found"].append(guid)

    if not guid_to_nid:
        logger.warning("Anki'de eşleşen not bulunamadı.")
        return result

    note_ids_to_delete = list(guid_to_nid.values())

    if dry_run:
        logger.info(f"[DRY-RUN] {len(note_ids_to_delete)} not Anki'den silinirdi.")
        result["deleted"] = list(guid_to_nid.keys())
        return result

    try:
        anki_request("deleteNotes", notes=note_ids_to_delete)
        result["deleted"] = list(guid_to_nid.keys())
        logger.info(f"✅ Anki'den silindi: {len(result['deleted'])} not")
    except Exception as e:
        logger.error(f"Anki silme hatası: {e}")
        result["errors"] = list(guid_to_nid.keys())

    return result


# ─── Pinecone Helpers ──────────────────────────────────────────────────────────

def delete_from_pinecone(guids: List[str], namespace: str, dry_run: bool = False) -> int:
    """GUID listesini Pinecone'dan siler. Silinen sayısını döner."""
    if not guids:
        return 0

    if dry_run:
        logger.info(f"[DRY-RUN] {len(guids)} vektör Pinecone'dan silinirdi (ns={namespace})")
        return len(guids)

    deleted = 0
    for i in range(0, len(guids), BATCH_SIZE):
        batch = guids[i : i + BATCH_SIZE]
        try:
            index.delete(ids=batch, namespace=namespace)
            deleted += len(batch)
            logger.info(f"Pinecone silindi: {deleted}/{len(guids)} (ns={namespace})")
        except Exception as e:
            logger.error(f"Pinecone silme hatası (batch {i}): {e}")

    return deleted


def update_manifest(guids: List[str], namespace: str):
    """Silinen GUID'leri manifest'ten kaldırır."""
    if not MANIFEST_PATH.exists():
        return

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    removed = 0
    for guid in guids:
        key = f"{namespace}::{guid}"
        if key in manifest:
            del manifest[key]
            removed += 1

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"Manifest güncellendi: {removed} kayıt kaldırıldı.")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_guids_from_file(path: Path) -> List[str]:
    """Her satırda bir GUID olan dosyadan GUID listesi okur."""
    guids = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            g = line.strip()
            if g and not g.startswith("#"):
                guids.append(g)
    return guids


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Windows UTF-8 fix
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Anki + Pinecone'dan kart silme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/anki_delete.py --file to_delete.txt --ns protez
  python scripts/anki_delete.py --guids "z!Zx)KuOg6" "B-OVGzEaX1" --ns radyoloji
  python scripts/anki_delete.py --file to_delete.txt --ns protez --dry-run
  python scripts/anki_delete.py --file to_delete.txt --ns protez --pinecone-only
  python scripts/anki_delete.py --file to_delete.txt --ns protez --anki-only
        """
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="GUID listesi dosyası (her satır bir GUID)")
    group.add_argument("--guids", nargs="+", help="Silinecek GUID'ler (boşlukla ayrılmış)")

    parser.add_argument("--ns", type=str, required=True, help="Pinecone namespace (örn: protez)")
    parser.add_argument("--dry-run", action="store_true", help="Gerçekten silme, sadece raporla")
    parser.add_argument("--pinecone-only", action="store_true", help="Sadece Pinecone'dan sil, Anki'ye dokunma")
    parser.add_argument("--anki-only", action="store_true", help="Sadece Anki'den sil, Pinecone'a dokunma")
    args = parser.parse_args()

    namespace = args.ns.lower().strip()

    # GUID listesini belirle
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"Dosya bulunamadı: {file_path}")
            sys.exit(1)
        guids = load_guids_from_file(file_path)
    else:
        guids = args.guids

    if not guids:
        logger.error("Silinecek GUID bulunamadı.")
        sys.exit(1)

    # Deduplicate
    guids = list(dict.fromkeys(guids))
    logger.info(f"Silinecek GUID sayısı: {len(guids)}")

    if args.dry_run:
        logger.info("[DRY-RUN MODU AKTIF] Hiçbir şey silinmeyecek.")

    # ── Anki silme ───────────────────────────────────────────────────────────
    anki_deleted = []
    if not args.pinecone_only:
        ac_available = check_ankiconnect()
        if not ac_available:
            if args.anki_only:
                logger.error("AnkiConnect erişilemiyor, işlem durduruluyor.")
                sys.exit(1)
            else:
                logger.warning(
                    "AnkiConnect erişilemiyor. Pinecone silme devam edecek, "
                    "Anki silme atlanıyor. Anki'yi açıp tekrar deneyin."
                )
        else:
            anki_result = delete_from_anki(guids, dry_run=args.dry_run)
            anki_deleted = anki_result["deleted"]
            if anki_result["not_found"]:
                logger.warning(
                    f"Anki'de bulunamayan GUID'ler ({len(anki_result['not_found'])}): "
                    + ", ".join(anki_result["not_found"][:5])
                    + ("..." if len(anki_result["not_found"]) > 5 else "")
                )

    # ── Pinecone silme ───────────────────────────────────────────────────────
    pinecone_deleted = 0
    if not args.anki_only:
        pinecone_deleted = delete_from_pinecone(guids, namespace, dry_run=args.dry_run)

    # ── Manifest güncelle ────────────────────────────────────────────────────
    if not args.dry_run and not args.anki_only:
        update_manifest(guids, namespace)

    # ── Özet ─────────────────────────────────────────────────────────────────
    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{prefix}✅ İşlem tamamlandı.")
    if not args.pinecone_only:
        print(f"  Anki'den silinen    : {len(anki_deleted)} not")
    if not args.anki_only:
        print(f"  Pinecone'dan silinen: {pinecone_deleted} vektör (ns={namespace})")


if __name__ == "__main__":
    main()
