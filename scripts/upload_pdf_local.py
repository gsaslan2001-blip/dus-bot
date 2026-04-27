import os
import sys
import argparse
from pypdf import PdfReader
from pinecone import Pinecone

# Scripts dizinini ekle
sys.path.append(os.path.dirname(__file__))
from embedding_utils import local_embedder
from config import PINECONE_API_KEY, MYPPDFS_HOST

def upload_pdf(pdf_path, namespace):
    """
    Yerel E5 modelini kullanarak PDF dosyasını parçalar ve Pinecone'a yükler.
    """
    if not os.path.exists(pdf_path):
        print(f"HATA: Dosya bulunamadı -> {pdf_path}")
        return

    print(f"[*] PDF okunuyor: {os.path.basename(pdf_path)}")
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        total_pages = len(reader.pages)
        for i, page in enumerate(reader.pages):
            if i % 20 == 0:
                print(f"  [>] Sayfa {i}/{total_pages} okunuyor...")
            content = page.extract_text()
            if content:
                full_text += content + "\n"
    except Exception as e:
        print(f"HATA: PDF okunamadı: {e}")
        return

    if not full_text.strip():
        print("HATA: PDF içinde metin bulunamadı.")
        return

    # Chunking (1000 karakter, 200 overlap)
    chunk_size = 1000
    overlap = 200
    chunks = []
    for i in range(0, len(full_text), chunk_size - overlap):
        chunk = full_text[i:i + chunk_size]
        if len(chunk.strip()) > 10:
            chunks.append(chunk)

    print(f"[*] Toplam {len(chunks)} parça oluşturuldu. Yerel E5 ile vektörleniyor...")

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=MYPPDFS_HOST)

    # Batch yükleme
    batch_size = 16 # Yerel CPU için makul bir değer
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        try:
            # Yerel E5 ile vektörleri üret
            vectors = local_embedder.embed_batch(batch)
            
            records = []
            for j, val in enumerate(vectors):
                # Deterministik ID (dosya adı + index)
                chunk_id = f"pdf-{os.path.basename(pdf_path)}-{i+j}"
                records.append({
                    "id": chunk_id,
                    "values": val,
                    "metadata": {
                        "text": batch[j],
                        "source": os.path.basename(pdf_path),
                        "type": "pdf_local_upload",
                        "namespace": namespace
                    }
                })
            
            index.upsert(vectors=records, namespace=namespace)
            print(f"  [+] {i + len(batch)} / {len(chunks)} parça yüklendi...")
            
        except Exception as e:
            print(f"  [!] Batch yükleme hatası: {e}")

    print(f"\n[✅] BAŞARI: '{os.path.basename(pdf_path)}' dosyası '{namespace}' namespace'ine yüklendi.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF dosyasını yerel E5 ile Pinecone'a yükler.")
    parser.add_argument("pdf_path", help="PDF dosyasının tam yolu")
    parser.add_argument("namespace", help="Pinecone namespace (örn: patoloji, cerrahi)")
    
    if len(sys.argv) < 3:
        parser.print_help()
        sys.exit(1)
        
    args = parser.parse_args()
    upload_pdf(args.pdf_path, args.namespace)
