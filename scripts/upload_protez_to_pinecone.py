import os
import uuid
import time
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP
import pypdf

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

target_dir = r"C:\Users\FURKAN\Desktop\DUS\protez\Yeni klasör\Parcalanmis"
namespace = "protez"

def extract_text_from_pdf(file_path):
    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

records = []
pdf_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.pdf')]

print(f"Found {len(pdf_files)} PDF files. Extracting text...")

for file in pdf_files:
    file_path = os.path.join(target_dir, file)
    print(f"Processing: {file}")
    
    content = extract_text_from_pdf(file_path)
    if not content.strip():
        print(f"Skipping {file} (no text extracted)")
        continue
        
    chunks = chunk_text(content)
    for i, chunk in enumerate(chunks):
        safe_id = f"protez-{uuid.uuid4().hex}"
        record = {
            "id": safe_id,
            "text": chunk,
            "source": file,
            "chunk_index": i
        }
        records.append(record)

print(f"Total chunks to upload: {len(records)}")

batch_size = 50  # Smaller batch size for better stability with integrated inference limits
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    print(f"Upserting batch {i//batch_size + 1}/{len(records)//batch_size + 1}...")
    
    attempt = 0
    max_retries = 5
    while attempt < max_retries:
        try:
            index.upsert_records(namespace, records=batch)
            break
        except Exception as e:
            attempt += 1
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = 2 ** attempt * 5
                print(f"Rate limit hit. Waiting {wait_time}s... (Attempt {attempt})")
                time.sleep(wait_time)
            else:
                print(f"Error upserting batch: {e}")
                break

print("Upload complete.")
