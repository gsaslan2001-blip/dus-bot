"""
auto_sync_dus.py — Günlük otomatik sync (Windows Task Scheduler tarafından çağrılır)
Sadece son 25 saatte değişen dosyaları yükler (mtime kontrolü manifest'te).
"""
import subprocess, sys, logging
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(__file__).parent.parent / "logs" / "auto_sync.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def run_uploader(extra_args: list[str] = []) -> int:
    script = Path(__file__).parent / "dus_uploader.py"
    cmd = [sys.executable, str(script)] + extra_args
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout:
        logging.info(result.stdout.strip())
    if result.stderr:
        logging.warning(result.stderr.strip())
    return result.returncode

if __name__ == "__main__":
    logging.info("=== Günlük DUS sync başladı ===")
    
    # 1. DUS → mybrain (sadece değişenler, force yok)
    rc1 = run_uploader([])
    logging.info(f"DUS sync tamamlandı. Return code: {rc1}")

    # 2. TELOS → mybrain/telos
    rc2 = run_uploader(["--telos"])
    logging.info(f"TELOS sync tamamlandı. Return code: {rc2}")

    # 3. vektörlenecek/ → chathistory
    rc3 = run_uploader(["--chathistory"])
    logging.info(f"chathistory sync tamamlandı. Return code: {rc3}")
    
    logging.info("=== Sync bitti ===\n")
