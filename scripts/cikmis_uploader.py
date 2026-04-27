"""
cikmis_uploader.py — dus_jsonlari/*.json → myppdfs index (cikmis namespace)
Yerel Multilingual-E5-Large kullanarak tüm çıkmış soruları vektörler.
"""

import os, sys, json, argparse, time
from pathlib import Path
from datetime import datetime

# ── Yol Sabitleri ─────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
PROJECT_DIR   = SCRIPT_DIR.parent
JSON_DIR      = PROJECT_DIR / "dus_jsonlari"
MYPPDFS_HOST  = "myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io"

# ── Pinecone & Local E5 ───────────────────────────────────────────────────────
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from config import PINECONE_API_KEY
except ImportError:
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")

from pinecone import Pinecone

def _get_local_embedder():
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from sentence_transformers import SentenceTransformer
    
    # E5-Large Snapshot yolu (Sistemdeki sabit yol)
    E5_SNAPSHOT = (
        r"C:\Users\FURKAN\.cache\huggingface\hub"
        r"\models--intfloat--multilingual-e5-large"
        r"\snapshots\3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3"
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[embedder] Yerel E5 yükleniyor ({device})...", flush=True)
    model = SentenceTransformer(E5_SNAPSHOT, device=device, local_files_only=True)
    print("[embedder] Model hazır.", flush=True)
    return model

_e5_model = None
def get_e5_model():
    global _e5_model
    if _e5_model is None:
        _e5_model = _get_local_embedder()
    return _e5_model

def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts: return []
    model = get_e5_model()
    # E5 passage prefix'i zorunlu
    prefixed = [f"passage: {t}" if not t.startswith("passage: ") else t for t in texts]
    return model.encode(prefixed, normalize_embeddings=True).tolist()

# ── Pinecone Init ─────────────────────────────────────────────────────────────
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

# ── İşlem Mantığı ─────────────────────────────────────────────────────────────
def process_json_file(file_path: Path, dry_run: bool = False):
    print(f"\n📂 İşleniyor: {file_path.name}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ❌ Hata: {file_path.name} okunamadı: {e}")
        return 0

    if not isinstance(data, list):
        print(f"  ⚠️ Uyarı: {file_path.name} bir liste değil, atlanıyor.")
        return 0

    vectors = []
    for q in data:
        # ID kontrolü
        qid = q.get("id") or f"dus_{q.get('yil')}_{q.get('soru_no')}"
        
        # Text oluşturma (Arama için zenginleştirilmiş metin)
        # Eğer JSON'da raw_text varsa onu kullan, yoksa oluştur
        raw_text = q.get("raw_text")
        if not raw_text:
            soru = q.get("soru_metni", "")
            secenekler = q.get("secenekler", {})
            opt_str = " ".join([f"{k}) {v}" for k, v in secenekler.items()])
            raw_text = f"{soru} {opt_str}".strip()
        
        if not raw_text:
            continue

        # Metadata hazırlama
        meta = {
            "text": raw_text,
            "doc_type": "cikmis_soru",
            "source_json": file_path.name,
            "yil": str(q.get("yil", "")),
            "donem": q.get("donem", ""),
            "bolum": q.get("bolum", ""),
            "ders": q.get("ders", ""),
            "soru_no": q.get("soru_no", 0),
            "iptal": q.get("iptal", False)
        }
        
        # None değerleri temizle (Pinecone metadata null sevmez)
        meta = {k: v for k, v in meta.items() if v is not None}
        
        vectors.append({
            "id": qid,
            "text": raw_text, # Embedding için geçici
            "metadata": meta
        })

    if not vectors:
        return 0

    if dry_run:
        print(f"  [DRY-RUN] {len(vectors)} soru hazırlandı.")
        return len(vectors)

    # Embedding al (Batch)
    texts_to_embed = [v["text"] for v in vectors]
    print(f"  [embed] {len(texts_to_embed)} soru vektörleniyor...")
    embeddings = embed_batch(texts_to_embed)

    # Upsert hazırlığı
    upsert_list = []
    for v, emb in zip(vectors, embeddings):
        upsert_list.append({
            "id": v["id"],
            "values": emb,
            "metadata": v["metadata"]
        })

    # Pinecone'a yükle (Batch size 50)
    batch_size = 50
    for i in range(0, len(upsert_list), batch_size):
        batch = upsert_list[i:i + batch_size]
        index.upsert(vectors=batch, namespace="cikmis")
        print(f"  ✓ Batch {i//batch_size + 1} yüklendi ({len(batch)} soru)")
        time.sleep(0.1)

    return len(vectors)

def main():
    parser = argparse.ArgumentParser(description="DUS JSON → Pinecone Uploader")
    parser.add_argument("--dry-run", action="store_true", help="Yükleme yapmadan sadece tara")
    parser.add_argument("--file", type=str, help="Sadece belirli bir JSON dosyasını işle")
    args = parser.parse_args()

    if not JSON_DIR.exists():
        print(f"❌ Dizin bulunamadı: {JSON_DIR}")
        sys.exit(1)

    json_files = []
    if args.file:
        target = JSON_DIR / args.file
        if target.exists():
            json_files.append(target)
        else:
            print(f"❌ Dosya bulunamadı: {args.file}")
            sys.exit(1)
    else:
        json_files = list(JSON_DIR.glob("*-dus.json"))
        # Alfabetik sırala
        json_files.sort()

    total_uploaded = 0
    start_time = time.time()

    for jf in json_files:
        total_uploaded += process_json_file(jf, args.dry_run)

    duration = time.time() - start_time
    print(f"\n✨ İşlem Tamamlandı!")
    print(f"🚀 Toplam Soru: {total_uploaded}")
    print(f"⏱️ Süre: {duration:.1f} saniye")
    print(f"📦 Index: myppdfs | Namespace: cikmis")

if __name__ == "__main__":
    main()
