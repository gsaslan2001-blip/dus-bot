
import torch
from sentence_transformers import SentenceTransformer

def test_embedding():
    model_name = "intfloat/multilingual-e5-large"
    print(f"Loading model: {model_name}...")
    model = SentenceTransformer(model_name)
    
    text = "DUS Mentörü test mesajı."
    # E5 models expect "query: " or "passage: " prefix depending on the task
    # For indexing (passage), we use "passage: "
    embedding = model.encode([f"passage: {text}"])
    
    print(f"Embedding shape: {embedding.shape}")
    print(f"Vector dimension: {len(embedding[0])}")
    
    if len(embedding[0]) == 1024:
        print("SUCCESS: Dimension matches Pinecone index (1024).")
    else:
        print(f"WARNING: Dimension mismatch. Expected 1024, got {len(embedding[0])}.")

if __name__ == "__main__":
    test_embedding()
