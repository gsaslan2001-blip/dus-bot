
import os
import sys
from pinecone import Pinecone

def reset_namespaces():
    print("🧹 MyBrain Reset Protocol başlatılıyor...")
    
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
    MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io")

    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY bulunamadı!")
        return

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=MYBRAIN_HOST)
    
    # Guncel namespace listesi (Gemini.MD)
    namespaces = [
        "dus-curriculum", "dus-memory", "dus-progress", 
        "dus-strategy", "dus-reference", "telos", 
        "chathistory", "claude-profile"
    ]
    
    print("⚠️ DİKKAT: Bu işlem aşağıdaki namespace'leri TAMAMEN SİLECEKTİR:")
    for ns in namespaces:
        print(f"  - {ns}")
    
    confirm = input("Emin misiniz? (evet/HAYIR): ")
    if confirm.lower() != "evet":
        print("İptal edildi.")
        return

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
