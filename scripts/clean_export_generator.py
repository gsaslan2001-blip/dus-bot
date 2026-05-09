import sys
import argparse
import logging
from pathlib import Path

# anki_parser modülünü import edebilmek için script dizinini yola ekle
SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from anki_parser import parse_line
except ImportError:
    logging.error("anki_parser.py bulunamadı. Lütfen aynı dizinde olduğundan emin olun.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Kopya (silinen) GUID'leri hariç tutarak temiz Anki TXT exportu oluşturur.")
    parser.add_argument("--input_txt", required=True, help="Orijinal Anki export TXT dosyası")
    parser.add_argument("--to_delete", required=True, help="Silinecek GUID'leri içeren dosya (to_delete.txt)")
    parser.add_argument("--output_txt", required=True, help="Temizlenmiş çıktı TXT dosyası (örn: xx_temiz.txt)")
    parser.add_argument("--ders", required=True, help="Ders/branş adı (parser için gerekli)")
    parser.add_argument("--unite", required=True, help="Ünite adı (parser için gerekli)")
    
    args = parser.parse_args()
    
    input_txt_path = Path(args.input_txt)
    to_delete_path = Path(args.to_delete)
    output_txt_path = Path(args.output_txt)
    
    if not input_txt_path.exists():
        logger.error(f"Girdi dosyası bulunamadı: {input_txt_path}")
        sys.exit(1)
        
    deleted_guids = set()
    if to_delete_path.exists():
        with open(to_delete_path, "r", encoding="utf-8") as f:
            for line in f:
                guid = line.strip()
                if guid:
                    deleted_guids.add(guid)
        logger.info(f"{len(deleted_guids)} adet silinecek GUID yüklendi.")
    else:
        logger.warning(f"to_delete dosyası bulunamadı: {to_delete_path}. Hiçbir kart silinmeyecek.")
        
    kept_count = 0
    skipped_count = 0
    total_count = 0
    
    output_txt_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(input_txt_path, "r", encoding="utf-8", errors="replace") as f_in, \
         open(output_txt_path, "w", encoding="utf-8") as f_out:
         
        for line in f_in:
            line_stripped = line.strip()
            if line_stripped.startswith("#") or not line_stripped:
                f_out.write(line) # Yorum satırlarını veya boş satırları koru
                continue
                
            total_count += 1
            card = parse_line(line_stripped, args.ders, args.unite)
            
            if card is None:
                # Parse edilemeyen satırları da koruyalım
                f_out.write(line)
                continue
                
            if card["guid"] in deleted_guids:
                skipped_count += 1
                continue
                
            f_out.write(line)
            kept_count += 1
            
    logger.info(f"İşlem tamamlandı. Toplam: {total_count}, Korunan: {kept_count}, Silinen: {skipped_count}")
    logger.info(f"Temiz dosya oluşturuldu: {output_txt_path}")

if __name__ == "__main__":
    main()
