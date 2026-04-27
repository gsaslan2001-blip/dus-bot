
import os
import sys
import time
from pinecone import Pinecone

# Scripts dizinini yola ekle
sys.path.append(os.path.dirname(__file__))
from config import PINECONE_API_KEY, MYPPDFS_HOST

def test_reranker():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=MYPPDFS_HOST)

    # Test sorusu (Tıbbi bir konu)
    query = "Pulpitis irreversibilis belirtileri ve ayırıcı tanısı"

    print(f"\n🔍 Test Sorgusu: {query}")
    print("=" * 60)

    # 1. AŞAMA: NORMAL ARAMA (DENSE)
    start_time = time.time()
    
    # Embedding oluştur
    query_embedding = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[query],
        parameters={"input_type": "query"}
    )
    
    # Sorgu yap
    dense_results = index.query(
        namespace="endodonti",
        vector=query_embedding[0].values,
        top_k=10,
        include_metadata=True
    )
    dense_time = time.time() - start_time

    print(f"📌 SADECE DENSE (E5-LARGE) | Süre: {dense_time:.2f}s")
    for i, match in enumerate(dense_results.matches):
        text = match.metadata.get('text', 'Metin yok').replace('\n', ' ')[:100]
        print(f"{i+1}. [Skor: {match.score:.4f}] {text}...")

    # 2. AŞAMA: RERANKING
    print("\n" + "=" * 60)
    start_time = time.time()
    
    documents = [match.metadata.get('text', '') for match in dense_results.matches]
    
    rerank_response = pc.inference.rerank(
        model="bge-reranker-v2-m3",
        query=query,
        documents=documents,
        top_n=5
    )
    rerank_time = time.time() - start_time

    print(f"🚀 RERANKER (BGE-V2-M3) | Süre: {rerank_time:.2f}s")
    for i, result in enumerate(rerank_response.data):
        orig_match = dense_results.matches[result.index]
        text = orig_match.metadata.get('text', '').replace('\n', ' ')[:100]
        print(f"{i+1}. [Yeniden Sıralanan Skor: {result.score:.4f}] (Eski Sıra: {result.index + 1}) {text}...")

    print("\n📊 ANALİZ:")
    print(f"- Toplam Ek Gecikme: {rerank_time:.2f} saniye")
    if rerank_response.data[0].index != 0:
        print(f"- 💡 Reranker sıralamayı değiştirdi! Orijinal {rerank_response.data[0].index + 1}. sonuç başa çekildi.")
    else:
        print("- Sıralama değişmedi ancak skorlar güncellendi.")

if __name__ == "__main__":
    test_reranker()
