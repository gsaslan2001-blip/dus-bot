import os
import sys
import argparse
from pinecone import Pinecone

# Pinecone API Config
PINECONE_API_KEY = 'pcsk_57q66M_WwyxH5mHedvLaJtZnRsNCb1S2BbMCoiL2ytwid6ycamgHgmY3ZKt9Sd7oVFEny'
pc = Pinecone(api_key=PINECONE_API_KEY)
INDEX_NAME = 'myppdfs'
NAMESPACE = 'dus-cikmis'

def perform_search(query: str, top_k: int = 10):
    try:
        index = pc.Index(INDEX_NAME)
        
        print(f"\n[!] Arama yapılıyor: '{query}'")
        
        # 1. Embedding (Pinecone Inference API)
        print("[!] Soru vektörleştiriliyor (multilingual-e5-large)...")
        embed_res = pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[query],
            parameters={"input_type": "query"}
        )
        query_vector = embed_res[0].values
        
        # 2. Vector Search
        print("[!] Pinecone'da benzer sorular aranıyor...")
        search_res = index.query(
            namespace=NAMESPACE,
            vector=query_vector,
            top_k=top_k * 2,  # Reranking için daha fazla getiriyoruz
            include_metadata=True
        )
        
        if not search_res.get("matches"):
            print("[-] Eşleşen sonuç bulunamadı.")
            return

        # 3. Reranking
        print("[!] Sonuçlar yeniden sıralanıyor (Reranking)...")
        documents = [m["metadata"].get("text", "") for m in search_res["matches"] if "text" in m.get("metadata", {})]
        
        if not documents:
            print("[-] Metin verisi içeren eşleşme bulunamadı.")
            return

        rank_res = pc.inference.rerank(
            model="bge-reranker-v2-m3",
            query=query,
            documents=documents,
            top_n=top_k,
            return_documents=True
        )

        # 4. Sonuçları Eşleştirme ve Frekans Analizi
        print("\n" + "="*50)
        print(f"SORGULANAN KAVRAM: {query}")
        print("="*50)
        
        ders_frekans = {}
        yil_frekans = {}

        print("\n--- İLGİLİ ÇIKMIŞ SORULAR ---\n")
        
        # Reranker'dan gelen dokümanları metadata ile eşleştirelim
        for rank_idx, doc in enumerate(rank_res.data):
            original_text = doc.document.text
            metadata = None
            
            # Orijinal metni metadata ile bulmak için eşleştirme yap
            for m in search_res["matches"]:
                if m["metadata"].get("text", "") == original_text:
                    metadata = m["metadata"]
                    break
                    
            if metadata:
                ders = metadata.get("ders", "Bilinmeyen")
                yil = metadata.get("yil", "Bilinmeyen")
                soru_no = metadata.get("soru_no", "?")
                score = doc.score
                
                # Frekansları topla
                ders_frekans[ders] = ders_frekans.get(ders, 0) + 1
                yil_frekans[yil] = yil_frekans.get(yil, 0) + 1
                
                print(f"[{rank_idx + 1}] Yıl: {yil} | Ders: {ders} | Soru No: {soru_no} | İlgi Skoru: {score:.3f}")
                print(f"Soru: {original_text[:200]}...\n")
                
        # 5. Frekans Analizi Çıktısı
        print("="*50)
        print("KAVRAMIN İSTATİSTİKSEL FREKANS ANALİZİ")
        print("="*50)
        
        print("\n=> Ders Dağılımı:")
        for d, count in sorted(ders_frekans.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {d}: {count} kez")
            
        print("\n=> Yıllara Göre Sıklık:")
        for y, count in sorted(yil_frekans.items(), key=lambda x: str(x[0]), reverse=True):
            print(f"   - {y}: {count} kez")

    except Exception as e:
        print(f"[!] Arama sırasında bir hata oluştu: {e}")


def main():
    parser = argparse.ArgumentParser(description="DUS Çıkmış Sorular - Semantik Kavram Arama Motoru")
    parser.add_argument("query", type=str, nargs="+", help="Aranacak konu, kavram veya terim (örn: 'Nodi submentales')")
    parser.add_argument("--limit", type=int, default=5, help="Getirilecek en alakalı soru sayısı (Varsayılan: 5)")
    
    args = parser.parse_args()
    
    full_query = " ".join(args.query)
    perform_search(full_query, top_k=args.limit)

if __name__ == "__main__":
    main()
