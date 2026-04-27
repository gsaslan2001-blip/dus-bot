
import os
import hashlib
import sys
import datetime
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP
from embedding_utils import embedder
import pypdf

# Initialize Pinecone
if not PINECONE_API_KEY:
    print("❌ PINECONE_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")
    sys.exit(1)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

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

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"❌ PDF Okuma Hatası ({pdf_path}): {e}")
    return text

def upload_directory(source_dir, namespace, category):
    print(f"\n📂 Yükleme başlatılıyor: {source_dir} -> Namespace: {namespace} (Category: {category})")
    if not os.path.exists(source_dir):
        print(f"⚠️ Dizin bulunamadı: {source_dir}")
        return

    all_data = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for file in os.listdir(source_dir):
        file_path = os.path.join(source_dir, file)
        if os.path.isdir(file_path): continue
        
        content = ""
        if file.lower().endswith('.md') or file.lower().endswith('.txt'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"❌ Okuma hatası ({file}): {e}")
        elif file.lower().endswith('.pdf'):
            content = extract_text_from_pdf(file_path)
        
        if not content.strip():
            continue
            
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            # Deterministic ID: hash of filename + chunk index
            # This ensures that if we re-upload the same file, it overwrites old chunks
            path_hash = hashlib.sha256(file.encode()).hexdigest()[:12]
            safe_id = f"{category[:4]}-{path_hash}-{i}"
            
            metadata = {
                "text": chunk,
                "source": file,
                "category": category,
                "date": today,
                "chunk_index": i
            }
            
            all_data.append({
                "id": safe_id,
                "metadata": metadata
            })

    if not all_data:
        print("ℹ️ Yüklenecek kayıt bulunamadı.")
        return

    print(f"✅ Toplam {len(all_data)} parça hazırlandı. Yerel embedding ve yükleme başlıyor...")
    
    batch_size = 25 # Smaller batch for stability
    for i in range(0, len(all_data), batch_size):
        batch = all_data[i:i + batch_size]
        texts = [item["metadata"]["text"] for item in batch]
        
        try:
            embeddings = embedder.embed_batch(texts)
            vectors_to_upsert = []
            for j, item in enumerate(batch):
                vectors_to_upsert.append({
                    "id": item["id"],
                    "values": embeddings[j],
                    "metadata": item["metadata"]
                })
            
            index.upsert(vectors=vectors_to_upsert, namespace=namespace)
            print(f"🚀 {namespace}: {min(i+batch_size, len(all_data))}/{len(all_data)} tamamlandı.")
            
        except Exception as e:
            print(f"❌ Hata (Upsert) {namespace}: {e}")

if __name__ == "__main__":
    # Example usage (can be called with arguments or configured here)
    if len(sys.argv) > 3:
        src = sys.argv[1]
        ns = sys.argv[2]
        cat = sys.argv[3]
        upload_directory(src, ns, cat)
    else:
        print("Kullanım: python universal_uploader.py <source_dir> <namespace> <category>")
