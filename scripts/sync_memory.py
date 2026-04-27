
import os
import hashlib
import sys
import datetime
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYBRAIN_HOST, CHUNK_SIZE, CHUNK_OVERLAP
from embedding_utils import embedder

# Initialize Pinecone
if not PINECONE_API_KEY:
    print("❌ PINECONE_API_KEY bulunamadı!")
    sys.exit(1)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYBRAIN_HOST)

def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            last_newline = text.rfind('\n', start, end)
            if last_newline != -1 and last_newline > start + (max_chars // 2):
                end = last_newline
        
        chunks.append(text[start:end].strip())
        start = end - overlap
        if start >= len(text):
            break
    return [c for c in chunks if c]

def get_deterministic_id(file_relative_path, chunk_index):
    # Create a stable ID based on the file path to allow overwriting (upsert)
    path_hash = hashlib.sha256(file_relative_path.encode()).hexdigest()[:16]
    return f"mem-{path_hash}-{chunk_index}"

def sync_directory(root_dir, namespace="claude_memory"):
    print(f"\n🧠 Hafıza Senkronizasyonu Başlıyor: {root_dir}")
    print(f"🎯 Hedef Namespace: {namespace}")
    
    if not os.path.exists(root_dir):
        print(f"⚠️ Dizin bulunamadı: {root_dir}")
        return

    all_vectors = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if not (file.lower().endswith('.md') or file.lower().endswith('.txt') or file.lower().endswith('.json')):
                continue
                
            file_path = os.path.join(dirpath, file)
            rel_path = os.path.relpath(file_path, root_dir)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"❌ Okuma hatası ({rel_path}): {e}")
                continue
            
            if not content.strip():
                continue
                
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                safe_id = get_deterministic_id(rel_path, i)
                
                metadata = {
                    "text": chunk,
                    "source": rel_path,
                    "type": "claude_memory",
                    "date": today,
                    "chunk_index": i
                }
                
                all_vectors.append({
                    "id": safe_id,
                    "metadata": metadata
                })

    if not all_vectors:
        print("ℹ️ Senkronize edilecek yeni/güncel veri bulunamadı.")
        return

    print(f"✅ Toplam {len(all_vectors)} parça hazırlandı. Vektörleme ve Pinecone yüklemesi başlıyor...")
    
    batch_size = 20
    for i in range(0, len(all_vectors), batch_size):
        batch = all_vectors[i:i + batch_size]
        texts = [item["metadata"]["text"] for item in batch]
        
        try:
            # Local Embedding (E5)
            embeddings = embedder.embed_batch(texts)
            
            vectors_to_upsert = []
            for j, item in enumerate(batch):
                vectors_to_upsert.append({
                    "id": item["id"],
                    "values": embeddings[j],
                    "metadata": item["metadata"]
                })
            
            # Upsert (Eski ID varsa üzerine yazar)
            index.upsert(vectors=vectors_to_upsert, namespace=namespace)
            print(f"🚀 {min(i+batch_size, len(all_vectors))}/{len(all_vectors)} tamamlandı.")
            
        except Exception as e:
            print(f"❌ Yükleme hatası: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        ns = sys.argv[2] if len(sys.argv) > 2 else "claude_memory"
        sync_directory(target_dir, ns)
    else:
        claude_base = r"C:\Users\FURKAN\.claude"
        mappings = [
            (os.path.join(claude_base, "skills"), "claude_memory"),
            (os.path.join(claude_base, "MEMORY"), "claude_memory"),
            (os.path.join(claude_base, "DUS"), "dus-data"),
            (os.path.join(claude_base, "projects"), "claude_memory"),
        ]
        print("🧠 Varsayılan senkronizasyon başlıyor...")
        for src, ns in mappings:
            sync_directory(src, ns)
        print("\n✅ Tüm senkronizasyonlar tamamlandı.")
