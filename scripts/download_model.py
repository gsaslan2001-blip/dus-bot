"""
Multilingual-E5-Large model indirme scripti.
.incomplete dosyaları temizler ve modeli yeniden indirir.
Sadece PyTorch ağırlıklarını alır (ONNX/OpenVINO atlanır).
"""

import os
import glob
import sys

CACHE_DIR = r"C:\Users\FURKAN\.cache\huggingface\hub"
MODEL_NAME = "intfloat/multilingual-e5-large"

def clean_incomplete():
    pattern = os.path.join(CACHE_DIR, "models--intfloat--multilingual-e5-large", "blobs", "*.incomplete")
    files = glob.glob(pattern)
    if not files:
        print("✅ Temizlenecek .incomplete dosya yok.")
        return
    for f in files:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"  Siliniyor: {os.path.basename(f)} ({size_mb:.0f} MB)")
        os.remove(f)
    print(f"🧹 {len(files)} incomplete dosya temizlendi.")

def download_model():
    from huggingface_hub import snapshot_download

    print(f"\n📥 Model indiriliyor: {MODEL_NAME}")
    print("  Atlanan: onnx/*, openvino/*, *.msgpack, flax_model*, tf_model*, rust_model*")
    print("  Bu işlem internet bağlantısına bağlı olarak 5-20 dakika sürebilir...\n")

    local_path = snapshot_download(
        repo_id=MODEL_NAME,
        cache_dir=CACHE_DIR,
        ignore_patterns=[
            "onnx/*", "openvino/*",
            "*.msgpack", "flax_model*", "tf_model*", "rust_model*",
        ],
    )
    print(f"\n✅ Model başarıyla indirildi: {local_path}")
    return local_path

def verify_model(local_path):
    from sentence_transformers import SentenceTransformer
    print("\n🔍 Model doğrulanıyor...")
    model = SentenceTransformer(local_path, device="cpu")
    vec = model.encode(["passage: DUS sınavı doğrulama testi."], normalize_embeddings=True)
    dim = len(vec[0])
    print(f"✅ Model çalışıyor! Boyut: {dim}")
    assert dim == 1024, f"Beklenen 1024, gelen {dim}"
    print("✅ Boyut doğrulandı: 1024")

if __name__ == "__main__":
    print("=" * 60)
    print("  Multilingual-E5-Large Model İndirici")
    print("=" * 60)

    if "--skip-clean" not in sys.argv:
        clean_incomplete()

    if "--clean-only" in sys.argv:
        print("Temizlik tamamlandı, indirme atlanıyor.")
        sys.exit(0)

    local_path = download_model()
    verify_model(local_path)
    print("\n🚀 Script tamamlandı. embedding_utils.py artık çalışmaya hazır.")
