import os
import uuid
import time
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP
import pypdf

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

# Source directory containing all Periodontology materials
source_dir = r"C:\Users\FURKAN\Desktop\DUS\Periodontoloji"
namespace = "periodontoloji"

# Already indexed files in Pinecone (to avoid duplicates)
already_indexed = [
    "7.b - İleri Cerrahi İşlemler 2.pdf",
    "7.c - İleri Cerrahi İşlemler 3.pdf",
    "8.a - Destekleyici Periodontal Tedavi.pdf"
]

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
all_pdfs = []

print(f"Searching for PDF files in {source_dir}...")

# Walk through the directory and its subdirectories
for root, dirs, files in os.walk(source_dir):
    # Skip 'literatür' and 'üretim' (production) directories
    if 'literatür' in root.lower() or 'üretim' in root.lower():
        continue
        
    for file in files:
        if file.lower().endswith('.pdf'):
            # Basic check to avoid duplicates from different folders (e.g., 'perio' folder copies)
            if file in already_indexed:
                print(f"Skipping already indexed file: {file}")
                continue
            
            # Additional check: if we already added a file with this name in this run
            if any(p[1] == file for p in all_pdfs):
                print(f"Skipping duplicate filename in this run: {file} (from {root})")
                continue
                
            all_pdfs.append((os.path.join(root, file), file))

print(f"Found {len(all_pdfs)} new PDF files to process. Extracting text...")

for file_path, file_name in all_pdfs:
    print(f"Processing: {file_name}")
    
    content = extract_text_from_pdf(file_path)
    if not content.strip():
        print(f"Skipping {file_name} (no text extracted)")
        continue
        
    chunks = chunk_text(content)
    for i, chunk in enumerate(chunks):
        # Use a deterministic-ish ID if possible or just UUID
        # Using filename + index helps if we need to track, but hex is safer for length
        safe_id = f"perio-{uuid.uuid4().hex}"
        record = {
            "id": safe_id,
            "text": chunk,
            "source": file_name,
            "chunk_index": i
        }
        records.append(record)

print(f"Total chunks to upload: {len(records)}")

if not records:
    print("No new chunks to upload. Exiting.")
    exit()

batch_size = 50 
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    print(f"Upserting batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1}...")
    
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
