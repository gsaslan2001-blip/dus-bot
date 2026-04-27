import os
import uuid
import sys
from pypdf import PdfReader
from pinecone import Pinecone

# Scripts klasörüne yolu ekle ki config import edilebilsin
sys.path.append(os.path.dirname(__file__))
from config import PINECONE_API_KEY, MYPPDFS_HOST, CHUNK_SIZE, CHUNK_OVERLAP

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=MYPPDFS_HOST)

pdf_path = r"C:\Users\FURKAN\Desktop\DUS\Cerrahi\2026 ADÇ KONU ANLATIMI.pdf"
namespace = "cerrahi"

def extract_text_from_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

def main():
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    print(f"Reading PDF: {pdf_path}")
    try:
        content = extract_text_from_pdf(pdf_path)
        print(f"Extracted {len(content)} characters.")
        
        if len(content.strip()) < 100:
            print("Warning: Extracted text is very short. PDF might be scanned without OCR.")
    except Exception as e:
        print(f"Error extracting text: {e}")
        return

    chunks = chunk_text(content)
    print(f"Total chunks to upload: {len(chunks)}")

    records = []
    for i, chunk in enumerate(chunks):
        safe_id = f"cer-{uuid.uuid4().hex[:8]}-{i}" # Shorter IDs are fine
        record = {
            "id": safe_id,
            "text": chunk,
            "source": os.path.basename(pdf_path),
            "chunk_index": i,
            "category": "cerrahi"
        }
        records.append(record)

    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        print(f"Upserting batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}...")
        try:
            index.upsert_records(namespace, records=batch)
        except Exception as e:
            print(f"Error upserting batch: {e}")

    print(f"Upload complete. {len(records)} chunks added to namespace '{namespace}'.")

if __name__ == "__main__":
    main()
