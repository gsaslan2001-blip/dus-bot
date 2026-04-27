import os
import uuid
import time
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

# Specific file and namespace
file_path = r"C:\Users\FURKAN\Desktop\DUS\Radyoloji\RADYOMD\RADYOLOJİ.md"
namespace = "radyoloji"

def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

records = []
filename = os.path.basename(file_path)

if os.path.exists(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            safe_id = f"radyo-{uuid.uuid4().hex}"
            record = {
                "id": safe_id,
                "text": chunk,
                "source": filename,
                "chunk_index": i,
                "category": "radyoloji"
            }
            records.append(record)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
else:
    print(f"File not found: {file_path}")

if records:
    print(f"Total chunks to upload: {len(records)}")
    
    import time
    batch_size = 20  # Reduced batch size to stay under token limits
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        print(f"Upserting batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                index.upsert_records(namespace, records=batch)
                break # Success
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)
                    print(f"Rate limit hit, waiting {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"Error upserting batch: {e}")
                    import traceback
                    traceback.print_exc()
                    break
        
        time.sleep(2) # Small delay between batches

    print("Upload complete.")
else:
    print("No records found to upload.")
