import os
import uuid
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

source_dir = r"C:\Users\FURKAN\Desktop\DUS\Endodonti\endo mdler"
namespace = "endodonti"

def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

records = []
print(f"Reading files from: {source_dir}")

for file in os.listdir(source_dir):
    if file.endswith('.md') or file.endswith('.txt'):
        file_path = os.path.join(source_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                safe_id = f"endo-{uuid.uuid4().hex}"
                record = {
                    "id": safe_id,
                    "text": chunk,
                    "source": file,
                    "chunk_index": i,
                    "category": "endodonti"
                }
                records.append(record)
        except Exception as e:
            print(f"Error reading {file}: {e}")

print(f"Total chunks to upload: {len(records)}")

if not records:
    print("No records found to upload.")
    exit()

batch_size = 50
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    print(f"Upserting batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}...")
    try:
        index.upsert_records(namespace, records=batch)
    except Exception as e:
        print(f"Error upserting batch: {e}")

print("Upload complete. Endodonti records are now indexed in 'myppdfs' index under 'endodonti' namespace.")
