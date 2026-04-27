
import os
import sys
from pinecone import Pinecone
from config import PINECONE_API_KEY, MYBRAIN_HOST

def reset_namespaces():
    print("🧹 MyBrain Reset Protocol başlatılıyor...")
    
    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY bulunamadı!")
        return

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=MYBRAIN_HOST)
    
    namespaces = ["claude_memory", "dus-data"]
    
    for ns in namespaces:
        try:
            print(f"🗑️ Namespace siliniyor: {ns}...")
            # Delete all records in the namespace
            index.delete(delete_all=True, namespace=ns)
            print(f"✅ {ns} başarıyla temizlendi.")
        except Exception as e:
            print(f"⚠️ {ns} temizlenirken hata oluştu (belki zaten boş): {e}")

if __name__ == "__main__":
    reset_namespaces()
