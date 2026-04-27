"""
dus_uploader.py — .claude/DUS → mybrain Pinecone (Yerel E5)
Manifest tabanlı overwrite: dosya değiştiğinde eski chunk'lar silinir, yenisi yazılır.

Kullanım:
  python scripts/dus_uploader.py --dry-run
  python scripts/dus_uploader.py                      # tümünü sync et
  python scripts/dus_uploader.py --namespace dus-progress
  python scripts/dus_uploader.py --file PROGRESS.md
  python scripts/dus_uploader.py --chathistory        # vektörlenecek/ → chathistory
"""

import os, sys, json, re, hashlib, argparse, time
from pathlib import Path
from datetime import datetime

# ── Yol sabitleri ─────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
PROJECT_DIR   = SCRIPT_DIR.parent
DUS_ROOT      = Path(r"C:\Users\FURKAN\.claude\DUS")
TELOS_ROOT    = Path(r"C:\Users\FURKAN\.claude\PAI\USER\TELOS")
VEKTORLENECEK = Path(r"C:\Users\FURKAN\Desktop\Projeler\Pinecone\vektörlenecek")
MANIFEST_PATH = PROJECT_DIR / "scripts" / "dus_manifest.json"
MYBRAIN_HOST  = "mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io"

# ── Pinecone ──────────────────────────────────────────────────────────────────
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from config import PINECONE_API_KEY
except ImportError:
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")

from pinecone import Pinecone

# Sadece local embedder — Llama/bulut singleton'u atla
import sys as _sys, importlib as _importlib
# embedding_utils modül-düzeyinde singleton başlatmasını engellemek için
# doğrudan LocalE5Embedder sınıfını yükleyip örnekliyoruz
def _get_local_embedder():
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from sentence_transformers import SentenceTransformer
    E5_SNAPSHOT = (
        r"C:\Users\FURKAN\.cache\huggingface\hub"
        r"\models--intfloat--multilingual-e5-large"
        r"\snapshots\3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3"
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[embedder] Local E5 yükleniyor ({device})...", flush=True)
    model = SentenceTransformer(E5_SNAPSHOT, device=device, local_files_only=True)
    print("[embedder] Model hazır.", flush=True)
    return model

_e5_model = None
def get_e5_model():
    global _e5_model
    if _e5_model is None:
        _e5_model = _get_local_embedder()
    return _e5_model

def embed_batch_local(texts: list[str], is_query: bool = False) -> list[list[float]]:
    if not texts:
        return []
    model = get_e5_model()
    prefix = "query: " if is_query else "passage: "
    prefixed = [t if t.startswith(prefix) else f"{prefix}{t}" for t in texts]
    return model.encode(prefixed, normalize_embeddings=True).tolist()

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYBRAIN_HOST)

# ── Namespace Routing ─────────────────────────────────────────────────────────
# Her dosya/dizin → hangi namespace + doc_type
NS_RULES = [
    # (glob pattern veya prefix, namespace, doc_type, lesson)
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
    ("",                                  "dus-strategy",   "strategy_doc",    None),  # fallback
]

SKIP_DIRS  = {".git", "__pycache__", ".mypy_cache", "memory/WORK"}
SKIP_EXTS  = {".py", ".json", ".yaml", ".yml", ".ps1", ".sh", ".txt"}
VALID_EXTS = {".md"}

# ── Chunking ──────────────────────────────────────────────────────────────────
MAX_CHARS    = 1600  # ~400 token @ 4 char/tok
OVERLAP_CHARS = 200

def smart_chunk(text: str, source_file: str) -> list[str]:
    """Başlık sınırında böl, tablo/kod bloklarını koru."""
    if len(text) <= MAX_CHARS:
        return [text.strip()]

    # Başlıklarda böl (## veya ###)
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
            # Bölüm kendisi çok büyükse paragraf bazlı böl
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

    # Kısa chunk'ları filtrele
    return [c for c in chunks if len(c) >= 80] or [text[:MAX_CHARS].strip()]

# ── ID & Metadata ─────────────────────────────────────────────────────────────
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

def make_id(namespace: str, rel_path: str, chunk_idx: int) -> str:
    h = hashlib.sha256(rel_path.encode()).hexdigest()[:8]
    prefix = NS_PREFIX.get(namespace, "xx")
    return f"{prefix}::{h}::{chunk_idx:03d}"

def route_file(rel_path: str) -> tuple[str, str, str | None]:
    """rel_path → (namespace, doc_type, lesson)"""
    norm = rel_path.replace("\\", "/")
    for pattern, ns, dtype, lesson in NS_RULES:
        if pattern and pattern in norm:
            return ns, dtype, lesson
    return "dus-strategy", "strategy_doc", None

def build_metadata(rel_path: str, chunk_text: str, chunk_idx: int,
                   total_chunks: int, namespace: str, doc_type: str,
                   lesson: str | None, mtime: str) -> dict:
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

# ── Manifest ──────────────────────────────────────────────────────────────────
def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_manifest(manifest: dict):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

# ── Pinecone Upsert / Delete ──────────────────────────────────────────────────
BATCH_SIZE = 50

def upsert_chunks(vectors: list[dict], namespace: str, dry_run: bool):
    if dry_run:
        print(f"    [DRY-RUN] upsert {len(vectors)} chunk → ns={namespace}")
        return
    for i in range(0, len(vectors), BATCH_SIZE):
        batch = vectors[i:i + BATCH_SIZE]
        index.upsert(vectors=batch, namespace=namespace)
        time.sleep(0.1)

def delete_ids(ids: list[str], namespace: str, dry_run: bool):
    if not ids:
        return
    if dry_run:
        print(f"    [DRY-RUN] delete {len(ids)} eski chunk ← ns={namespace}")
        return
    for i in range(0, len(ids), BATCH_SIZE):
        index.delete(ids=ids[i:i + BATCH_SIZE], namespace=namespace)

# ── Tek Dosya İşle ────────────────────────────────────────────────────────────
def process_file(filepath: Path, root: Path, manifest: dict,
                 dry_run: bool, force: bool,
                 namespace_filter: str | None = None,
                 chathistory_mode: bool = False,
                 telos_mode: bool = False) -> int:
    """Dosyayı chunk'la, embed et, upsert et. Eklenen chunk sayısını döndür."""
    rel_path = str(filepath.relative_to(root))
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d")

    if chathistory_mode:
        namespace, doc_type, lesson = "chathistory", "chat_note", None
    elif telos_mode:
        namespace, doc_type, lesson = "telos", "user_telos", None
    else:
        namespace, doc_type, lesson = route_file(rel_path)

    if namespace_filter and namespace != namespace_filter:
        return 0

    manifest_key = f"{namespace}::{rel_path}"

    # Değişmedi mi? (force değilse atla)
    if not force and manifest_key in manifest:
        stored_mtime = manifest[manifest_key].get("mtime", "")
        if stored_mtime == mtime:
            return 0  # Değişmemiş, atla

    text = filepath.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return 0

    chunks = smart_chunk(text, rel_path)
    total  = len(chunks)

    # Eski chunk'ları sil
    old_ids = manifest.get(manifest_key, {}).get("ids", [])
    delete_ids(old_ids, namespace, dry_run)

    # Dry-run: embedding atla, sadece say
    if dry_run:
        print(f"  [DRY-RUN] {rel_path} → {namespace} ({total} chunk)")
        return total

    # Embed — sadece local E5
    vectors_raw = embed_batch_local([f"passage: {c}" for c in chunks], is_query=False)

    # Vektör listesi hazırla
    new_ids = []
    upsert_list = []
    for idx, (chunk, vec) in enumerate(zip(chunks, vectors_raw)):
        vid = make_id(namespace, rel_path, idx)
        new_ids.append(vid)
        meta = build_metadata(rel_path, chunk, idx, total, namespace, doc_type, lesson, mtime)
        upsert_list.append({"id": vid, "values": vec, "metadata": meta})

    upsert_chunks(upsert_list, namespace, dry_run)

    # Manifest güncelle
    if not dry_run:
        manifest[manifest_key] = {"mtime": mtime, "ids": new_ids, "namespace": namespace}

    print(f"  ✓ {rel_path} → {namespace} ({total} chunk)", flush=True)
    return total

# ── Dizin Tara ────────────────────────────────────────────────────────────────
def should_skip(path: Path, root: Path) -> bool:
    rel = str(path.relative_to(root)).replace("\\", "/")
    for skip in SKIP_DIRS:
        if skip in rel:
            return True
    return False

def scan_dir(root: Path, manifest: dict, dry_run: bool, force: bool,
             namespace_filter: str | None, 
             chathistory_mode: bool = False,
             telos_mode: bool = False) -> int:
    total_chunks = 0
    for filepath in root.rglob("*"):
        if not filepath.is_file():
            continue
        if filepath.suffix not in VALID_EXTS:
            continue
        if should_skip(filepath, root):
            continue
        total_chunks += process_file(
            filepath, root, manifest, dry_run, force,
            namespace_filter, chathistory_mode, telos_mode
        )
    return total_chunks

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="DUS → mybrain uploader")
    parser.add_argument("--dry-run",    action="store_true", help="Yükleme yapma, sadece say")
    parser.add_argument("--force",      action="store_true", help="mtime fark etmeksizin tümünü yeniden yükle")
    parser.add_argument("--namespace",  type=str, default=None,
                        help="Sadece belirtilen namespace (örn: dus-progress)")
    parser.add_argument("--file",       type=str, default=None,
                        help="Sadece bu dosya (örn: PROGRESS.md)")
    parser.add_argument("--chathistory",action="store_true",
                        help="vektörlenecek/ → chathistory namespace")
    parser.add_argument("--telos",      action="store_true",
                        help="PAI/USER/TELOS/ → telos namespace")
    args = parser.parse_args()

    manifest = load_manifest()
    total = 0

    if args.chathistory:
        print(f"\n=== vektörlenecek/ → chathistory ===")
        if not VEKTORLENECEK.exists():
            print("  vektörlenecek/ bulunamadı, atlanıyor.")
        else:
            total += scan_dir(VEKTORLENECEK, manifest, args.dry_run, args.force,
                              "chathistory", chathistory_mode=True)
    elif args.telos:
        print(f"\n=== PAI/USER/TELOS → telos ===")
        if not TELOS_ROOT.exists():
            print("  TELOS dizini bulunamadı.")
        else:
            total += scan_dir(TELOS_ROOT, manifest, args.dry_run, args.force,
                              "telos", telos_mode=True)
    else:
        print(f"\n=== .claude/DUS → mybrain ===")
        if args.file:
            # Tek dosya modu
            matches = list(DUS_ROOT.rglob(args.file))
            if not matches:
                print(f"Dosya bulunamadı: {args.file}")
                sys.exit(1)
            for fp in matches:
                total += process_file(fp, DUS_ROOT, manifest, args.dry_run,
                                      force=True,
                                      namespace_filter=args.namespace)
        else:
            total += scan_dir(DUS_ROOT, manifest, args.dry_run, args.force,
                              args.namespace)

    if not args.dry_run:
        save_manifest(manifest)

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Toplam: {total} chunk yüklendi.")

if __name__ == "__main__":
    main()
