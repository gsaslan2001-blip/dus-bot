"""
dus_uploader.py — .claude/DUS -> mybrain Pinecone (Pinecone Inference E5, 1024-dim)
Manifest tabanlı overwrite: dosya değiştiğinde eski chunk'lar silinir, yenisi yazılır.
"""

import os
import sys
import json
import re
import hashlib
import argparse
import time
import logging
import functools
import codecs
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from dotenv import load_dotenv

# --- Initialization & Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

# Local modules
try:
    from embedding_utils import get_embedder
except ImportError:
    logger.error("embedding_utils module not found. Make sure it is in SCRIPT_DIR.")
    sys.exit(1)

from pinecone import Pinecone

# --- Environment & Constants ---
HOME_DIR = Path.home()
DUS_ROOT = Path(os.environ.get("DUS_ROOT", HOME_DIR / ".claude" / "DUS"))
TELOS_ROOT = Path(os.environ.get("TELOS_ROOT", HOME_DIR / ".claude" / "PAI" / "USER" / "TELOS"))
VEKTORLENECEK = Path(os.environ.get("VEKTORLENECEK_ROOT", PROJECT_DIR / "vektörlenecek"))

MANIFEST_PATH = SCRIPT_DIR / "dus_manifest.json"
MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")

BATCH_SIZE = 96
MAX_CHARS = 1000
OVERLAP_CHARS = 200

# --- Clients ---
pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
index = pc.Index(host=MYBRAIN_HOST) if pc else None

# --- Namespace Routing ---
# In a real-world scenario, this could be loaded from an external JSON/YAML file.
NS_RULES = [
    ("memory/projects/user_profile.md",     "claude-profile", "user_profile",    None),
    ("memory/user_configuration.md",        "claude-profile", "user_profile",    None),
    ("memory/projects/user_preferences.md", "claude-profile", "user_pref",       None),
    ("memory/projects/user_sleep.md",       "claude-profile", "user_pref",       None),
    ("memory/projects/feedback_",           "dus-memory",     "feedback",        None),
    ("memory/projects/project_",            "dus-memory",     "project_memory",  None),
    ("memory/projects/reference_",          "dus-memory",     "reference_doc",   None),
    ("memory/projects/workflow_",           "dus-memory",     "workflow",        None),
    ("CURRICULUM/ENDODONTİ",               "dus-curriculum", "curriculum",      "endodonti"),
    ("CURRICULUM/PATOLOJİ",                "dus-curriculum", "curriculum",      "patoloji"),
    ("CURRICULUM/PATOLOJI",                "dus-curriculum", "curriculum",      "patoloji"),
    ("CURRICULUM/BİYOKİMYA",              "dus-curriculum", "curriculum",      "biyokimya"),
    ("CURRICULUM/CERRAHİ",                "dus-curriculum", "curriculum",      "cerrahi"),
    ("CURRICULUM/FARMAKOLOJİ",            "dus-curriculum", "curriculum",      "farmakoloji"),
    ("CURRICULUM/FİZYOLOJİ",             "dus-curriculum", "curriculum",      "fizyoloji"),
    ("CURRICULUM/HİSTOLOJİ",             "dus-curriculum", "curriculum",      "histoloji"),
    ("CURRICULUM/MİKROBİYOLOJİ",         "dus-curriculum", "curriculum",      "mikrobiyoloji"),
    ("CURRICULUM/ORTODONTİ",             "dus-curriculum", "curriculum",      "ortodonti"),
    ("CURRICULUM/PEDODONTİ",             "dus-curriculum", "curriculum",      "pedodonti"),
    ("CURRICULUM/PERİODONTOLOJİ",        "dus-curriculum", "curriculum",      "periodontoloji"),
    ("CURRICULUM/PROTEZ",                 "dus-curriculum", "curriculum",      "protez"),
    ("CURRICULUM/RADYOLOJİ",             "dus-curriculum", "curriculum",      "radyoloji"),
    ("CURRICULUM/RESTORATİF",            "dus-curriculum", "curriculum",      "restoratif"),
    ("CURRICULUM/",                       "dus-curriculum", "curriculum",      None),
    ("PROGRESS.md",                       "dus-progress",   "progress_tracker",None),
    ("DECISIONS.md",                      "dus-progress",   "strategy_doc",    None),
    ("STUCK_POINTS.md",                   "dus-progress",   "progress_tracker",None),
    ("GUNLUK/",                           "dus-progress",   "daily_note",      None),
    ("WEEKLY/",                           "dus-progress",   "weekly_review",   None),
    ("STRATEGY.md",                       "dus-strategy",   "strategy_doc",    None),
    ("MEMORY.md",                         "dus-strategy",   "strategy_doc",    None),
    ("INDEX.md",                          "dus-strategy",   "strategy_doc",    None),
    ("SYSTEMS/KONU/",                     "dus-curriculum", "curriculum",      None),
    ("REFERENCE/",                        "dus-reference",  "reference_tool",  None),
    ("SYSTEMS/",                          "dus-reference",  "reference_tool",  None),
    ("memory/",                           "dus-memory",     "project_memory",  None),
    ("",                                  "dus-strategy",   "strategy_doc",    None),
]

SKIP_DIRS = {".git", "__pycache__", ".mypy_cache", "memory/WORK"}
VALID_EXTS = {".md"}

NS_PREFIX = {
    "claude-profile": "cp",
    "dus-progress":   "dp",
    "dus-strategy":   "ds",
    "dus-curriculum": "dc",
    "dus-memory":     "dm",
    "dus-reference":  "dr",
    "chathistory":    "ch",
    "telos":          "tl",
}


# --- Decorators & Helpers ---
def retry_operation(retries: int = 3, delay: float = 1.0):
    """Ağ işlemlerinde hata anında tekrar deneme sağlayan decorator."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"[{func.__name__}] Başarısız (Deneme {attempt+1}/{retries}): {e}")
                    if attempt == retries - 1:
                        logger.error(f"[{func.__name__}] İşlem tamamen başarısız oldu.")
                        return None
                    time.sleep(delay)
        return wrapper
    return decorator


def embed_batch_pinecone_e5(texts: List[str], is_query: bool = False) -> List[List[float]]:
    if not texts:
        return []
    
    # Pinecone Inference API (multilingual-e5-large) batch limit is 96.
    # Process in batches of 90 to be safe.
    batch_size = 90
    all_embeddings = []
    embedder = get_embedder(provider="pinecone")
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info(f"[pinecone-embed] Processing embedding batch: {i}-{i + len(batch)} / {len(texts)}")
        embeddings = embedder.embed_batch(batch, is_query=is_query)
        all_embeddings.extend(embeddings)
        
    return all_embeddings


def embed_batch_local(texts: List[str], is_query: bool = False) -> List[List[float]]:
    """Backward-compatible alias. The active provider is Pinecone Inference E5, not a local model."""
    return embed_batch_pinecone_e5(texts, is_query=is_query)


def smart_chunk(text: str, source_file: str) -> List[str]:
    """Başlık sınırında böl, paragraf bazlı ilerle."""
    if len(text) <= MAX_CHARS:
        return [text.strip()]

    header_re = re.compile(r'(?=^#{1,3} )', re.MULTILINE)
    sections = header_re.split(text)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    current = ""
    for sec in sections:
        if len(current) + len(sec) + 2 <= MAX_CHARS:
            current = (current + "\n\n" + sec).strip()
        else:
            if current:
                chunks.append(current)
            if len(sec) > MAX_CHARS:
                paras = sec.split("\n\n")
                buf = ""
                for p in paras:
                    if len(buf) + len(p) + 2 <= MAX_CHARS:
                        buf = (buf + "\n\n" + p).strip()
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = p.strip()
                if buf:
                    chunks.append(buf)
            else:
                current = sec
    if current:
        chunks.append(current)

    return [c for c in chunks if len(c) >= 80] or [text[:MAX_CHARS].strip()]


def make_id(namespace: str, rel_path: str, chunk_idx: int) -> str:
    h = hashlib.sha256(rel_path.encode()).hexdigest()[:8]
    prefix = NS_PREFIX.get(namespace, "xx")
    return f"{prefix}::{h}::{chunk_idx:03d}"


def route_file(rel_path: str) -> Tuple[str, str, Optional[str]]:
    norm = rel_path.replace("\\", "/")
    for pattern, ns, dtype, lesson in NS_RULES:
        if pattern and pattern in norm:
            return ns, dtype, lesson
    return "dus-strategy", "strategy_doc", None


def build_metadata(rel_path: str, chunk_text: str, chunk_idx: int,
                   total_chunks: int, namespace: str, doc_type: str,
                   lesson: Optional[str], mtime: str) -> Dict[str, Any]:
    meta = {
        "text":         chunk_text,
        "source_file":  rel_path.replace("\\", "/"),
        "namespace":    namespace,
        "doc_type":     doc_type,
        "chunk_index":  chunk_idx,
        "total_chunks": total_chunks,
        "last_updated": mtime,
    }
    if lesson:
        meta["lesson"] = lesson
    return meta


# --- Manifest ---
def load_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: Dict[str, Any]):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Pinecone Operations ---
@retry_operation(retries=3, delay=1.0)
def upsert_batch(batch: List[Dict[str, Any]], namespace: str):
    if index:
        index.upsert(vectors=batch, namespace=namespace)

@retry_operation(retries=3, delay=1.0)
def delete_batch(batch: List[str], namespace: str):
    if index:
        index.delete(ids=batch, namespace=namespace)


def upsert_chunks(vectors: List[Dict[str, Any]], namespace: str, dry_run: bool):
    if dry_run:
        logger.info(f"[DRY-RUN] upsert {len(vectors)} chunk -> ns={namespace}")
        return
    if not index:
        logger.error("Pinecone client başlatılamadı (API Key yok).")
        return
    for i in range(0, len(vectors), BATCH_SIZE):
        upsert_batch(vectors[i:i + BATCH_SIZE], namespace)


def delete_ids(ids: List[str], namespace: str, dry_run: bool):
    if not ids:
        return
    if dry_run:
        logger.info(f"[DRY-RUN] delete {len(ids)} eski chunk <- ns={namespace}")
        return
    if not index:
        return
    for i in range(0, len(ids), BATCH_SIZE):
        delete_batch(ids[i:i + BATCH_SIZE], namespace)


# --- File Processing ---
def process_file(filepath: Path, root: Path, manifest: Dict[str, Any],
                 dry_run: bool, force: bool,
                 target_namespace: Optional[str] = None,
                 target_doc_type: Optional[str] = None,
                 target_lesson: Optional[str] = None) -> int:
    """Dosyayı chunk'la, embed et, upsert et. Eklenen chunk sayısını döndür."""
    rel_path = str(filepath.relative_to(root))
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S")

    # Routing
    if target_namespace and target_doc_type:
        namespace, doc_type, lesson = target_namespace, target_doc_type, target_lesson
    else:
        namespace, doc_type, lesson = route_file(rel_path)

    manifest_key = f"{namespace}::{rel_path}"


    text = filepath.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return 0

    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    manifest_entry = manifest.get(manifest_key, {})
    if not force and manifest_entry:
        if manifest_entry.get("sha256") == sha256:
            return 0
        # Backward compatibility for existing mtime-only manifest entries.
        if "sha256" not in manifest_entry and manifest_entry.get("mtime", "") == mtime:
            return 0

    chunks = smart_chunk(text, rel_path)
    total = len(chunks)

    old_ids = manifest.get(manifest_key, {}).get("ids", [])

    if dry_run:
        logger.info(f"[DRY-RUN] {rel_path} -> {namespace} ({total} chunk, would embed via Pinecone E5)")
        return total

    vectors_raw = embed_batch_pinecone_e5([f"passage: {c}" for c in chunks], is_query=False)

    new_ids = []
    upsert_list = []
    for idx, (chunk, vec) in enumerate(zip(chunks, vectors_raw)):
        vid = make_id(namespace, rel_path, idx)
        new_ids.append(vid)
        meta = build_metadata(rel_path, chunk, idx, total, namespace, doc_type, lesson, mtime)
        upsert_list.append({"id": vid, "values": vec, "metadata": meta})

    upsert_chunks(upsert_list, namespace, dry_run)

    stale_ids = [old_id for old_id in old_ids if old_id not in new_ids]
    delete_ids(stale_ids, namespace, dry_run)

    manifest[manifest_key] = {"mtime": mtime, "sha256": sha256, "ids": new_ids, "namespace": namespace}
    logger.info(f"[OK] {rel_path} -> {namespace} ({total} chunk)")
    return total


def should_skip(path: Path, root: Path) -> bool:
    rel = str(path.relative_to(root)).replace("\\", "/")
    return any(skip in rel for skip in SKIP_DIRS)


def scan_dir(root: Path, manifest: Dict[str, Any], dry_run: bool, force: bool,
             target_namespace: Optional[str] = None,
             target_doc_type: Optional[str] = None,
             target_lesson: Optional[str] = None) -> int:
    total_chunks = 0
    for filepath in root.rglob("*"):
        if not filepath.is_file() or filepath.suffix not in VALID_EXTS or should_skip(filepath, root):
            continue
        
        # If a specific namespace is requested via filter, and we are using auto-routing
        if target_namespace and not target_doc_type:
            ns, _, _ = route_file(str(filepath.relative_to(root)))
            if ns != target_namespace:
                continue

        total_chunks += process_file(
            filepath, root, manifest, dry_run, force,
            target_namespace if target_doc_type else None,
            target_doc_type, target_lesson
        )
    return total_chunks


# --- Main ---
def main():
    # Windows UTF-8 Fix
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="DUS -> mybrain uploader")
    parser.add_argument("--dry-run",    action="store_true", help="Yükleme yapma, sadece say")
    parser.add_argument("--force",      action="store_true", help="mtime fark etmeksizin tümünü yeniden yükle")
    parser.add_argument("--namespace",  type=str, default=None, help="Sadece belirtilen namespace (örn: dus-progress)")
    parser.add_argument("--file",       type=str, default=None, help="Sadece bu dosya (örn: PROGRESS.md)")
    parser.add_argument("--chathistory",action="store_true", help="vektörlenecek/ -> chathistory namespace")
    parser.add_argument("--telos",      action="store_true", help="PAI/USER/TELOS/ -> telos namespace")
    args = parser.parse_args()

    manifest = load_manifest()
    total = 0

    if args.chathistory:
        logger.info("=== vektörlenecek/ -> chathistory ===")
        if not VEKTORLENECEK.exists():
            logger.warning("vektörlenecek/ bulunamadı, atlanıyor.")
        else:
            total += scan_dir(VEKTORLENECEK, manifest, args.dry_run, args.force, 
                              target_namespace="chathistory", target_doc_type="chat_note")
    elif args.telos:
        logger.info("=== PAI/USER/TELOS -> telos ===")
        if not TELOS_ROOT.exists():
            logger.warning("TELOS dizini bulunamadı.")
        else:
            total += scan_dir(TELOS_ROOT, manifest, args.dry_run, args.force, 
                              target_namespace="telos", target_doc_type="user_telos")
    else:
        logger.info("=== .claude/DUS -> mybrain ===")
        if args.file:
            matches = list(DUS_ROOT.rglob(args.file))
            if not matches:
                logger.error(f"Dosya bulunamadı: {args.file}")
                sys.exit(1)
            for fp in matches:
                ns_filter = args.namespace
                ns, doc_type, lesson = route_file(str(fp.relative_to(DUS_ROOT)))
                if ns_filter and ns != ns_filter:
                    continue
                total += process_file(fp, DUS_ROOT, manifest, args.dry_run, force=True, 
                                      target_namespace=ns, target_doc_type=doc_type, target_lesson=lesson)
        else:
            total += scan_dir(DUS_ROOT, manifest, args.dry_run, args.force, target_namespace=args.namespace)

    if not args.dry_run:
        save_manifest(manifest)

    logger.info(f"{'[DRY-RUN] ' if args.dry_run else ''}Toplam: {total} chunk yüklendi.")


if __name__ == "__main__":
    main()
