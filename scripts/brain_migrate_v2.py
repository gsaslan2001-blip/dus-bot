
import os
import hashlib
import uuid
import sys
import datetime
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYBRAIN_HOST, CHUNK_SIZE, CHUNK_OVERLAP

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
        # Try to break at a newline if possible
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

    records = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for root, dirs, files in os.walk(source_dir):
        # Skip git and cache
        if any(x in root for x in ['.git', '__pycache__', 'backups', 'node_modules']):
            continue
            
        for file in files:
            # Sadece metin tabanlı dosyaları al
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
                        # Dosya yolundan sabit bir hash üret (ilk 12 karakter yeterli)
                        path_hash = hashlib.sha256(rel_path.encode()).hexdigest()[:12]
                        safe_id = f"mig-{path_hash}-{i}"
                        
                        record = {
                            "id": safe_id,
                            "text": chunk,
                            "source": f"migration/{rel_path}",
                            "type": record_type,
                            "date": today,
                            "file_path": rel_path,
                            "file_name": file,
                            "chunk_index": i
                        }
                        records.append(record)
                except Exception as e:
                    print(f"❌ Hata (Okuma) {file_path}: {e}")

    if not records:
        print("ℹ️ Yüklenecek kayıt bulunamadı.")
        return

    print(f"✅ Toplam {len(records)} parça hazırlandı. Yükleme başlıyor...")
    
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # Pinecone v7+ integrated inference upsert
            index.upsert_records(namespace, records=batch)
            print(f"🚀 {namespace}: {min(i+batch_size, len(records))}/{len(records)} tamamlandı.")
        except Exception as e:
            print(f"❌ Hata (Upsert) {namespace}: {e}")

if __name__ == "__main__":
    # Migration Mapping
    # Format: (Source Path, Namespace, Record Type)
    mappings = [
        (r"C:\Users\FURKAN\.claude\PAI", "claude_memory", "pai_core"),
        (r"C:\Users\FURKAN\.claude\DUS", "dus-data", "dus_strategy"),
        (r"C:\Users\FURKAN\.claude\MEMORY", "claude_memory", "user_history"),
        (r"C:\Users\FURKAN\.claude\projects", "claude_memory", "project_memory"),
        (r"C:\Users\FURKAN\Desktop\Personal_AI_Infrastructure-main", "claude_memory", "pai_infrastructure")
    ]
    
    print("🧠 MyBrain Migration Protocol v2.0 - Pinecone Sync")
    print("--------------------------------------------------")
    
    for src, ns, rtype in mappings:
        migrate_directory(src, ns, rtype)
        
    print("\n✨ Tüm göç işlemleri tamamlandı. MYBRAIN.MD protokolüne uygun olarak veriler senkronize edildi.")
