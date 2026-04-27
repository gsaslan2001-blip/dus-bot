
import os
import uuid
import sys
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

def migrate_directory(source_dir, namespace):
    print(f"\n📂 Tarama başlatılıyor: {source_dir} -> Namespace: {namespace}")
    if not os.path.exists(source_dir):
        print(f"⚠️ Dizin bulunamadı, atlanıyor: {source_dir}")
        return

    records = []
    for root, dirs, files in os.walk(source_dir):
        # Skip git and cache
        if any(x in root for x in ['.git', '__pycache__', 'backups']):
            continue
            
        for file in files:
            if file.endswith(('.md', '.txt', '.json')):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue
                        
                    chunks = chunk_text(content)
                    for i, chunk in enumerate(chunks):
                        safe_id = f"{namespace}-{uuid.uuid4().hex[:8]}-{i}"
                        record = {
                            "id": safe_id,
                            "text": chunk,
                            "metadata": {
                                "source": rel_path,
                                "type": "brain_migration",
                                "category": namespace,
                                "file_name": file,
                                "chunk_index": i
                            }
                        }
                        records.append(record)
                except Exception as e:
                    print(f"❌ Hata (Okuma) {file_path}: {e}")

    print(f"✅ Toplam {len(records)} parça hazırlandı. Yükleme başlıyor...")
    
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # Note: upsert_records uses the fieldMap defined in the index.
            # In our case, 'text' is the embedded field.
            # We pass the rest as metadata indirectly or directly depending on SDK version.
            # For integrated inference (v7+), we can pass a list of dicts.
            index.upsert_records(namespace, records=batch)
            print(f"🚀 {namespace}: {i+len(batch)}/{len(records)} tamamlandı.")
        except Exception as e:
            print(f"❌ Hata (Upsert) {namespace}: {e}")

if __name__ == "__main__":
    # Migration Mapping
    mappings = [
        (r"C:\Users\FURKAN\.claude\PAI", "pai-system"),
        (r"C:\Users\FURKAN\.claude\DUS", "dus-strategy"),
        (r"C:\Users\FURKAN\.claude\MEMORY", "user-memory"),
        (r"C:\Users\FURKAN\Desktop\Personal_AI_Infrastructure-main\Packs", "pai-skills")
    ]
    
    print("🧠 Second Brain - Pinecone Göçü Başlatılıyor...")
    for src, ns in mappings:
        migrate_directory(src, ns)
        
    print("\n✨ Tüm göç işlemleri tamamlandı.")
