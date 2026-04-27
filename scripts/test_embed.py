
import os
import sys
import time

print("--- STARTING TEST ---")
try:
    import torch
    print(f"Torch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
except ImportError:
    print("Torch not found")

try:
    from sentence_transformers import SentenceTransformer
    print("SentenceTransformer imported")
except ImportError:
    print("SentenceTransformer not found")

model_name = "intfloat/multilingual-e5-large"
print(f"Attempting to load model: {model_name} on CPU...")

start = time.time()
try:
    # Set environment variables to avoid some common hangs
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # Try loading with local_files_only=True first to see if it's already there
    # But for first time, it might need to download.
    model = SentenceTransformer(model_name, device="cpu")
    print(f"Model loaded successfully in {time.time() - start:.2f}s")
    
    emb = model.encode("Hello world")
    print(f"Embedding successful! Shape: {emb.shape}")
except Exception as e:
    print(f"Error: {e}")
print("--- ENDING TEST ---")
