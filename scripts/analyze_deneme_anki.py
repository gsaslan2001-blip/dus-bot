import os
import sys
import re
from dotenv import load_dotenv

# Set encoding for standard output and load .env
if sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    except Exception:
        pass

load_dotenv()

from pinecone import Pinecone
from embedding_utils import get_embedder

def parse_questions(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newline to get each question block
    blocks = content.split('\n\n')
    questions = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        # Try to extract question number for file naming
        match = re.match(r'^(\d+)', block)
        if match:
            q_num = match.group(1)
        else:
            q_num = f"unknown_{len(questions)+1}"
            
        questions.append((q_num, block))
        
    return questions

def analyze_questions():
    filepath = r"C:\Users\FURKAN\Desktop\DUS\Deneme Analizi\09.05.2026 deneme açıklamaları.md"
    questions = parse_questions(filepath)
    
    print(f"Toplam {len(questions)} soru bulundu.")
    
    # Initialize Pinecone and Embedder
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    anki_host = os.environ.get("ANKI_HOST", "anki-0crkhvy.svc.aped-4627-b74a.pinecone.io")
    index = pc.Index(host=anki_host)
    
    embedder = get_embedder(provider="openai", dimension=3072)
    
    namespaces = ["protez", "fizyoloji", "endodonti", "patoloji", "radyoloji", "histoloji", "periodontoloji"]
    
    # Create output directory
    out_dir = os.path.join(os.getcwd(), "vektörlenecek")
    os.makedirs(out_dir, exist_ok=True)
    
    for q_num, q_text in questions:
        print(f"Soru {q_num} analiz ediliyor...")
        try:
            # 1. Vectorize the question
            vec = embedder.embed_text(q_text, is_query=True)
            
            # 2. Search across namespaces
            all_matches = []
            for ns in namespaces:
                res = index.query(
                    namespace=ns,
                    vector=vec,
                    top_k=5,
                    include_metadata=True
                )
                if res.matches:
                    for m in res.matches:
                        # Append the namespace so we know where it came from
                        m.metadata["_namespace"] = ns
                        all_matches.append(m)
            
            # Remove exact duplicates based on ID or text if needed (we'll just rerank)
            if not all_matches:
                print(f"Soru {q_num} için eşleşen kart bulunamadı.")
                content = f"# Soru {q_num} Analizi\n\n## Soru Metni\n{q_text}\n\n## Anki Kartları\nBulunamadı."
                out_path = os.path.join(out_dir, f"deneme_analizi_09052026_soru_{q_num}.md")
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                continue
                
            # 3. Rerank top 15 matches across all namespaces
            all_matches.sort(key=lambda x: x.score, reverse=True)
            top_candidates = all_matches[:15]
            documents = [m.metadata.get("text", "") for m in top_candidates if "text" in m.metadata]
            
            # Handle potential empty texts
            if not documents:
                continue
                
            rank_res = pc.inference.rerank(
                model="bge-reranker-v2-m3",
                query=q_text,
                documents=documents,
                top_n=5,
                return_documents=True
            )
            
            # Extract final reranked cards
            final_cards = []
            for d in rank_res.data:
                # Find the original match to get namespace and other metadata
                original_match = next((m for m in top_candidates if m.metadata.get("text") == d.document.text), None)
                if original_match:
                    final_cards.append({
                        "score": d.score,
                        "text": d.document.text,
                        "namespace": original_match.metadata.get("_namespace", "unknown"),
                        "front": original_match.metadata.get("front", ""),
                        "back": original_match.metadata.get("back", ""),
                        "tags": original_match.metadata.get("tags", "")
                    })
                    
            # 4. Save to markdown
            out_path = os.path.join(out_dir, f"deneme_analizi_09052026_soru_{q_num}.md")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(f"# Soru {q_num} Analizi\n\n")
                f.write(f"## Soru Metni\n```\n{q_text}\n```\n\n")
                f.write(f"## Anki Kartları ({len(final_cards)} adet bulundu)\n\n")
                
                for i, card in enumerate(final_cards, 1):
                    f.write(f"### Kart {i} (Ders: {card['namespace']} | Rerank Skoru: {card['score']:.4f})\n")
                    f.write(f"**Ön Yüz:**\n{card['front']}\n\n")
                    f.write(f"**Arka Yüz:**\n{card['back']}\n\n")
                    f.write(f"**Etiketler:** {card['tags']}\n\n")
                    f.write(f"**Tam Metin:**\n{card['text']}\n\n")
                    f.write("---\n\n")
                    
            print(f"Soru {q_num} kaydedildi: {out_path}")
            
        except Exception as e:
            print(f"Soru {q_num} işlenirken hata oluştu: {e}")

if __name__ == "__main__":
    analyze_questions()
