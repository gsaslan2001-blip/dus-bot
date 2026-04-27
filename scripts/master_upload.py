"""
DUS Mentoru — Master Upload Script
Tum .claude ve proje dosyalarini yerel E5 + Pinecone mybrain'e yukler.
Kullanim:
  python scripts/master_upload.py           # tum kaynaklar
  python scripts/master_upload.py --dry-run # sadece sayim, yukleme yok
  python scripts/master_upload.py --source dus   # sadece dus-data namespace
"""

import os
import sys
import hashlib
import datetime
import argparse

# Windows UTF-8 fix — reconfigure instead of wrapping (no closed-file issue)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- Config import (env + hosts) ---
sys.path.insert(0, os.path.dirname(__file__))
from config import PINECONE_API_KEY, MYBRAIN_HOST, CHUNK_SIZE, CHUNK_OVERLAP
from embedding_utils import embedder

from pinecone import Pinecone

if not PINECONE_API_KEY:
    print("HATA: PINECONE_API_KEY bulunamadi. .env dosyasini kontrol et.")
    sys.exit(1)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYBRAIN_HOST)

# ---------------------------------------------------------------------------
# Kaynak dizinleri ve namespace eslestirmeleri
# ---------------------------------------------------------------------------
CLAUDE_BASE = r"C:\Users\FURKAN\.claude"
PROJECT_BASE = r"C:\Users\FURKAN\Desktop\Projeler\Pinecone"

SOURCES = [
    # (source_dir, namespace, record_type, recursive)
    (os.path.join(CLAUDE_BASE, "DUS"),       "dus-data",      "dus_strategy",    True),
    (os.path.join(CLAUDE_BASE, "agents"),    "claude_memory", "agent_definition", True),
    (os.path.join(CLAUDE_BASE, "MEMORY"),    "claude_memory", "user_memory",     True),
    (os.path.join(CLAUDE_BASE, "projects"),  "claude_memory", "project_memory",  True),
    (os.path.join(CLAUDE_BASE, "skills"),    "claude_memory", "skill_definition", True),
    (CLAUDE_BASE,                            "claude_memory", "claude_config",   False),  # sadece kok md
    (PROJECT_BASE,                           "claude_memory", "project_docs",    False),  # sadece kok md
]

SUPPORTED_EXTENSIONS = (".md", ".txt", ".json", ".yaml", ".yml")
SKIP_DIRS = {".git", "__pycache__", "node_modules", "backups", ".venv", "venv"}

# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar
# ---------------------------------------------------------------------------

def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            nl = text.rfind("\n", start, end)
            if nl != -1 and nl > start + CHUNK_SIZE // 2:
                end = nl
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
        if start >= len(text):
            break
    return chunks


def make_id(source_tag: str, rel_path: str, chunk_index: int) -> str:
    key = f"{source_tag}::{rel_path}"
    h = hashlib.sha256(key.encode()).hexdigest()[:14]
    return f"mu-{h}-{chunk_index}"


def collect_files(source_dir: str, recursive: bool) -> list[str]:
    if not os.path.isdir(source_dir):
        return []
    result = []
    if recursive:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.lower().endswith(SUPPORTED_EXTENSIONS):
                    result.append(os.path.join(root, f))
    else:
        for f in os.listdir(source_dir):
            path = os.path.join(source_dir, f)
            if os.path.isfile(path) and f.lower().endswith(SUPPORTED_EXTENSIONS):
                result.append(path)
    return result


def read_file(path: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return ""


# ---------------------------------------------------------------------------
# Ana yukleme fonksiyonu
# ---------------------------------------------------------------------------

def upload_source(source_dir: str, namespace: str, record_type: str,
                  recursive: bool, dry_run: bool = False) -> int:
    files = collect_files(source_dir, recursive)
    if not files:
        print(f"  [ATLANDI] {source_dir} — dosya bulunamadi")
        return 0

    all_records = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    source_tag = os.path.basename(source_dir)

    for file_path in files:
        content = read_file(file_path)
        if not content.strip():
            continue
        rel = os.path.relpath(file_path, source_dir)
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            all_records.append({
                "id": make_id(source_tag, rel, i),
                "text": chunk,
                "meta": {
                    "text": chunk,
                    "source": rel.replace("\\", "/"),
                    "type": record_type,
                    "namespace": namespace,
                    "date": today,
                    "chunk_index": i,
                },
            })

    total = len(all_records)
    print(f"  {source_dir}")
    print(f"    {len(files)} dosya -> {total} parca -> namespace: {namespace}")

    if dry_run or total == 0:
        return total

    batch_size = 32
    for i in range(0, total, batch_size):
        batch = all_records[i : i + batch_size]
        texts = [r["text"] for r in batch]
        try:
            embeddings = embedder.embed_batch(texts, is_query=False)
            vectors = [
                {"id": r["id"], "values": embeddings[j], "metadata": r["meta"]}
                for j, r in enumerate(batch)
            ]
            index.upsert(vectors=vectors, namespace=namespace)
            done = min(i + batch_size, total)
            print(f"    [{namespace}] {done}/{total} tamamlandi", end="\r")
        except Exception as e:
            print(f"\n    HATA (batch {i}): {e}")

    print(f"    [{namespace}] {total}/{total} tamamlandi      ")
    return total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DUS Mentoru Master Upload")
    parser.add_argument("--dry-run", action="store_true",
                        help="Sayim yap, Pinecone'a yukleme yapma")
    parser.add_argument("--source", choices=["dus", "agents", "memory", "skills",
                                              "projects", "config", "all"],
                        default="all", help="Hangi kaynagi yukle")
    args = parser.parse_args()

    source_filter = {
        "dus":      {"DUS"},
        "agents":   {"agents"},
        "memory":   {"MEMORY"},
        "skills":   {"skills"},
        "projects": {"projects", "Pinecone"},
        "config":   {".claude", "Pinecone"},
        "all":      None,
    }[args.source]

    print("=" * 60)
    print("  DUS Mentoru — Master Upload")
    print(f"  Mod: {'DRY-RUN' if args.dry_run else 'CANLI YUKLEME'}")
    print(f"  Kaynak filtresi: {args.source}")
    print("=" * 60)

    grand_total = 0
    for (src, ns, rtype, recursive) in SOURCES:
        src_name = os.path.basename(src)
        if source_filter and src_name not in source_filter:
            continue
        grand_total += upload_source(src, ns, rtype, recursive, dry_run=args.dry_run)

    print()
    print("=" * 60)
    if args.dry_run:
        print(f"  DRY-RUN tamamlandi. Toplam parca: {grand_total}")
        print("  Gercek yukleme icin: python scripts/master_upload.py")
    else:
        print(f"  Yukleme tamamlandi! Toplam: {grand_total} parca")
    print("=" * 60)


if __name__ == "__main__":
    main()
