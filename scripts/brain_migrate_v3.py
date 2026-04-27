
import os
import hashlib
import sys
import datetime
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYBRAIN_HOST, CHUNK_SIZE, CHUNK_OVERLAP
from embedding_utils import embedder

# Initialize Pinecone
if not PINECONE_API_KEY:
    print("❌ PINECONE_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")
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

def migrate_directory(source_dir, namespace, record_type):
    print(f"\n📂 Tarama başlatılıyor: {source_dir} -> Namespace: {namespace} (Type: {record_type})")
    if not os.path.exists(source_dir):
        print(f"⚠️ Dizin bulunamadı, atlanıyor: {source_dir}")
        return

    all_data = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for root, dirs, files in os.walk(source_dir):
        if any(x in root for x in ['.git', '__pycache__', 'backups', 'node_modules']):
            continue
            
        for file in files:
            if file.lower().endswith(('.md', '.txt', '.json', '.yaml', '.yml')):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue
                        
                    chunks = chunk_text(content)
                    for i, chunk in enumerate(chunks):
                        path_hash = hashlib.sha256(rel_path.encode()).hexdigest()[:12]
                        safe_id = f"mig-{path_hash}-{i}"
                        
                        # Metadata for Pinecone
                        metadata = {
                            "text": chunk,
                            "source": f"migration/{rel_path}",
                            "type": record_type,
                            "date": today,
                            "file_path": rel_path,
                            "file_name": file,
                            "chunk_index": i
                        }
                        
                        all_data.append({
                            "id": safe_id,
                            "metadata": metadata
                        })
                except Exception as e:
                    print(f"❌ Hata (Okuma) {file_path}: {e}")

    if not all_data:
        print("ℹ️ Yüklenecek kayıt bulunamadı.")
        return

    print(f"✅ Toplam {len(all_data)} parça hazırlandı. Yerel embedding ve yükleme başlıyor...")
    
    batch_size = 50
    for i in range(0, len(all_data), batch_size):
        batch = all_data[i:i + batch_size]
        
        # Extract texts for batch embedding
        texts = [item["metadata"]["text"] for item in batch]
        
        try:
            # Generate embeddings locally
            embeddings = embedder.embed_batch(texts)
            
            # Prepare vectors for Pinecone upsert
            vectors_to_upsert = []
            for j, item in enumerate(batch):
                vectors_to_upsert.append({
                    "id": item["id"],
                    "values": embeddings[j],
                    "metadata": item["metadata"]
                })
            
            # Upsert to Pinecone
            index.upsert(vectors=vectors_to_upsert, namespace=namespace)
            print(f"🚀 {namespace}: {min(i+batch_size, len(all_data))}/{len(all_data)} tamamlandı.")
            
        except Exception as e:
            print(f"❌ Hata (Embedding/Upsert) {namespace}: {e}")

if __name__ == "__main__":
    mappings = [
        (r"C:\Users\FURKAN\.claude\PAI", "claude_memory", "pai_core"),
        (r"C:\Users\FURKAN\.claude\DUS", "dus-data", "dus_strategy"),
        (r"C:\Users\FURKAN\.claude\MEMORY", "claude_memory", "user_history"),
        (r"C:\Users\FURKAN\.claude\projects", "claude_memory", "project_memory"),
        (r"C:\Users\FURKAN\Desktop\Personal_AI_Infrastructure-main", "claude_memory", "pai_infrastructure")
    ]
    
    print("🧠 MyBrain Migration Protocol v3.0 - Local Embedding Sync")
    print("---------------------------------------------------------")
    
    for src, ns, rtype in mappings:
        migrate_directory(src, ns, rtype)
        
    print("\n✨ Tüm göç işlemleri tamamlandı. Yerel embedding kullanılarak veriler senkronize edildi.")
