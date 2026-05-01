"""
anki_parser.py — Anki TXT export → Standart JSON
Hem Cloze-MAXXİNG hem Basic-AnKing formatlarını destekler.
Karışık export (aynı dosyada her iki format) otomatik ayrıştırılır.

Kullanım:
    python scripts/anki_parser.py "dosya.txt" --ders protez --unite dis_morfolojisi
    python scripts/anki_parser.py "dosya.txt" --ders radyoloji --unite radyoloji_fizigi
"""

import re
import sys
import json
import argparse
import codecs
import logging
from pathlib import Path

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Paths ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ANKI_JSONLAR = PROJECT_DIR / "anki_jsonlar"

# --- Kart Tipleri ---
CLOZE_TYPE = "Cloze-MAXXİNG"
BASIC_TYPE = "Basic-AnKing"
SUPPORTED_TYPES = {CLOZE_TYPE, BASIC_TYPE}

# --- Cloze Pattern ---
CLOZE_RE = re.compile(r"\{\{c\d+::([^:}]+)(?:::.*?)?\}\}")


def clean_cloze(text: str) -> str:
    """{{c1::X}} → X, {{c1::X::ipucu}} → X"""
    if not text:
        return ""
    return CLOZE_RE.sub(r"\1", text).strip()


def clean_html(text: str) -> str:
    """Basit HTML etiketlerini temizle (Anki bazen html:true ile export eder)."""
    if not text:
        return ""
    # <br> → boşluk, diğer tagları kaldır
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def clean_field(text: str) -> str:
    """Genel alan temizleme: HTML + baştaki/sondaki boşluk."""
    return clean_html(text).strip()


def parse_line(line: str, ders: str, unite: str, line_idx: int = 0) -> dict | None:
    """
    Tek bir Anki satırını parse edip standart JSON sözlüğü döndürür.
    Gelişmiş Format (GUID + NoteType + Deck + Alanlar...) veya
    Basit Format (Alanlar...) desteği sunar.
    """
    import hashlib

    parts = line.rstrip("\n").split("\t")
    if len(parts) < 1:
        return None

    # EĞER GELİŞMİŞ FORMAT (GUID ve NoteType içeren tam Anki Export) ise
    if len(parts) >= 4 and parts[1].strip() in SUPPORTED_TYPES:
        guid = parts[0].strip()
        notetype = parts[1].strip()
        deck_full = parts[2].strip()

        if notetype == CLOZE_TYPE:
            text_raw = clean_field(parts[3]) if len(parts) > 3 else ""
            baslik = clean_field(parts[4]) if len(parts) > 4 else ""
            extra = clean_field(parts[5]) if len(parts) > 5 else ""
        else:
            front = clean_field(parts[3]) if len(parts) > 3 else ""
            back = clean_field(parts[4]) if len(parts) > 4 else ""
            baslik = clean_field(parts[5]) if len(parts) > 5 else ""
            extra = ""
    
    # EĞER BASİT FORMAT (Sadece Soru/Cevap ve Başlık içeren dosya) ise
    else:
        # Metne göre GUID hash üret
        text_for_hash = parts[0].strip()
        guid = "hash_" + hashlib.md5(text_for_hash.encode("utf-8")).hexdigest()[:16]
        deck_full = f"{ders.capitalize()}::{unite.capitalize()}"
        
        # Cloze kart mı?
        if "{{" in text_for_hash and "}}" in text_for_hash:
            notetype = CLOZE_TYPE
            text_raw = clean_field(parts[0])
            baslik = clean_field(parts[1]) if len(parts) > 1 else ""
            extra = clean_field(parts[2]) if len(parts) > 2 else ""
        else:
            notetype = BASIC_TYPE
            front = clean_field(parts[0])
            back = clean_field(parts[1]) if len(parts) > 1 else ""
            baslik = clean_field(parts[2]) if len(parts) > 2 else ""
            extra = ""

    # Ortak Alan Yapılandırması
    if notetype == CLOZE_TYPE:
        text_clean = clean_cloze(text_raw)
        if not text_clean:
            return None
        vektorlenecek = f"{baslik} | {text_clean}" if baslik else text_clean

        return {
            "id": guid,
            "guid": guid,
            "ders": ders,
            "unite": unite,
            "deck_full": deck_full,
            "kart_tipi": "cloze",
            "text_raw": text_raw,
            "text_clean": text_clean,
            "baslik": baslik,
            "extra": extra,
            "vektorlenecek_metin": vektorlenecek,
        }
    else:
        if not front:
            return None
        text_clean = f"{front} {back}".strip() if back else front
        vektorlenecek = f"{baslik} | {text_clean}" if baslik else text_clean

        return {
            "id": guid,
            "guid": guid,
            "ders": ders,
            "unite": unite,
            "deck_full": deck_full,
            "kart_tipi": "basic",
            "front": front,
            "back": back,
            "baslik": baslik,
            "extra": extra,
            "text_clean": text_clean,
            "vektorlenecek_metin": vektorlenecek,
        }

    return None


def parse_file(input_path: Path, ders: str, unite: str) -> list[dict]:
    """Anki TXT export dosyasını parse eder, kart listesi döner."""
    cards = []
    skip_count = 0
    cloze_count = 0
    basic_count = 0

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            # Başlık satırlarını atla
            if line.startswith("#") or not line:
                continue

            card = parse_line(line, ders, unite)
            if card is None:
                skip_count += 1
                continue

            if card["kart_tipi"] == "cloze":
                cloze_count += 1
            else:
                basic_count += 1

            cards.append(card)

    logger.info(
        f"Parse tamamlandı: {len(cards)} kart "
        f"({cloze_count} Cloze, {basic_count} Basic, {skip_count} atlandı)"
    )
    return cards


def save_json(cards: list[dict], ders: str, unite: str) -> Path:
    """Kartları standart JSON dosyasına yazar, Path döner."""
    ANKI_JSONLAR.mkdir(parents=True, exist_ok=True)
    output_path = ANKI_JSONLAR / f"{ders}_{unite}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON yazıldı: {output_path} ({len(cards)} kart)")
    return output_path


def main():
    # Windows UTF-8 fix
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Anki TXT export → Standart JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/anki_parser.py "C:/anki/1-Morfoloji.txt" --ders protez --unite dis_morfolojisi
  python scripts/anki_parser.py "C:/anki/Radyoloji.txt" --ders radyoloji --unite radyoloji_fizigi
        """
    )
    parser.add_argument("input", type=str, help="Anki TXT export dosyası yolu")
    parser.add_argument("--ders", type=str, required=True, help="Ders/branş adı (küçük harf, Türkçe karakter yok)")
    parser.add_argument("--unite", type=str, required=True, help="Ünite adı (küçük harf, boşluk yerine _ kullan)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Dosya bulunamadı: {input_path}")
        sys.exit(1)

    if not input_path.suffix.lower() == ".txt":
        logger.warning("Dosya uzantısı .txt değil. Yine de devam ediliyor...")

    ders = args.ders.lower().strip()
    unite = args.unite.lower().strip().replace(" ", "_")

    logger.info(f"Parse başlıyor: {input_path.name} → ders={ders}, unite={unite}")
    cards = parse_file(input_path, ders, unite)

    if not cards:
        logger.error("Hiç kart parse edilemedi. Dosya formatını kontrol edin.")
        sys.exit(1)

    output_path = save_json(cards, ders, unite)
    print(f"\n✅ Başarılı: {len(cards)} kart → {output_path}")


if __name__ == "__main__":
    main()
