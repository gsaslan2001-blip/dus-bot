import os
import json
import uuid
import glob
from pinecone import Pinecone

api_key = 'pcsk_57q66M_WwyxH5mHedvLaJtZnRsNCb1S2BbMCoiL2ytwid6ycamgHgmY3ZKt9Sd7oVFEny'
pc = Pinecone(api_key=api_key)
index_name = 'myppdfs'
index = pc.Index(index_name)
namespace = 'dus-cikmis'

target_dir = r"C:\Users\FURKAN\Desktop\Projeler\Pinecone"

records = []
json_files = glob.glob(os.path.join(target_dir, "*dus.json"))

for file_path in json_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            
        for q in questions:
            # We construct a unique ID per question
            # Using year and soru_no to prevent duplicates
            yil = q.get("yil", "unknown")
            soru_no = q.get("soru_no", 0)
            safe_id = f"dus-{yil}-q{soru_no}-{uuid.uuid4().hex[:8]}"
            
            # Integrated inference requires a 'text' field as per fieldMap
            record = {
                "id": safe_id,
                "text": q["raw_text"],
                "soru_no": soru_no,
                "yil": str(yil),
                "ders": q.get("ders", "Bilinmeyen"),
                "filename": q.get("filename", os.path.basename(file_path))
            }
            records.append(record)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

print(f"Total questions to upload: {len(records)}")

batch_size = 96
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    print(f"Upserting batch {i//batch_size + 1}/{len(records)//batch_size + 1}...")
    try:
        index.upsert_records(namespace, records=batch)
    except Exception as e:
        print(f"Error upserting batch: {e}")

print("Upload complete.")
