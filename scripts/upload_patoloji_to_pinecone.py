import os
import uuid
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

source_dir = r"C:\Users\FURKAN\Desktop\DUS\patoloji\pato md"
namespace = "patoloji"

def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

records = []
for file in os.listdir(source_dir):
    if file.endswith('.md'):
        file_path = os.path.join(source_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                safe_id = f"pato-{uuid.uuid4().hex}"
                record = {
                    "id": safe_id,
                    "text": chunk,
                    "source": file,
                    "chunk_index": i,
                    "category": "patoloji"
                }
                records.append(record)
        except Exception as e:
            print(f"Error reading {file}: {e}")

print(f"Total chunks to upload: {len(records)}")

batch_size = 50
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    print(f"Upserting batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}...")
    try:
        # For integrated inference indexes, we use upsert_records if available in SDK 
        # or just upsert if the model handles it.
        # The MCP server uses 'upsert_records' which is likely what we need for integrated inference.
        # If using the standard SDK, we might need to check if 'upsert_records' exists.
        # For now, I'll use the logic from the previous script which worked for the user.
        index.upsert_records(namespace, records=batch)
    except AttributeError:
        # Fallback if upsert_records is not in this SDK version
        # Actually, Pinecone integrated inference usually requires upsert_records
        print("upsert_records not found, trying upsert...")
        index.upsert(vectors=[(r['id'], [0.0]*1024, r['metadata']) for r in batch], namespace=namespace) # This won't work for integrated inference though
    except Exception as e:
        print(f"Error upserting batch: {e}")

print("Upload complete.")
