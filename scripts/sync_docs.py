import shutil
import os

def sync_docs():
    source = "Gemini.MD"
    targets = ["CLAUDE.md", "agents.md"]
    
    if not os.path.exists(source):
        print(f"Hata: Kaynak dosya bulunamadı: {source}")
        return

    for target in targets:
        try:
            shutil.copy2(source, target)
            print(f"Başarılı: {source} -> {target} senkronize edildi.")
        except Exception as e:
            print(f"Hata: {target} kopyalanırken sorun oluştu: {e}")

if __name__ == "__main__":
    # Script root dizinde çalıştırılmalı (C:\Users\FURKAN\Desktop\Projeler\Pinecone)
    # Eğer scripts içinden çağrılırsa dizini ayarla
    current_dir = os.getcwd()
    if os.path.basename(current_dir) == "scripts":
        os.chdir("..")
    
    sync_docs()
