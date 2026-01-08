import json
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Paths
INPUT_FILE = Path("backend/data/final/legali_ready_v2.json")
OUTPUT_FILE = Path("backend/data/final/legali_vectors_v2.json")
MODEL_NAME = "BAAI/bge-base-en-v1.5"

def generate_embeddings():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} missing.")
        return

    print(f"Loading model: {MODEL_NAME}...")
    # Initialize model
    # Note: bge-base-en-v1.5 instructions say to prepend "Represent this sentence for searching relevant passages: " for queries.
    # But for indexing (documents), we just embed the text directly?
    # BGE instructions: "For the retrieval task... encode the query... encode the corpus..."
    # Usually for corpus we use simple encoding.
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"Loading chunks from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    texts = [c['text'] for c in chunks]
    ids = [c['id'] for c in chunks]
    
    print(f"Generating embeddings for {len(texts)} chunks...")
    # Encode
    # normalize_embeddings=True for cosine similarity?
    # BGE usually recommends normalize_embeddings=True
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    
    # Structure output
    # We want to save ID -> Vector mapping or List of Objects?
    # Common format: List of {id, vector, metadata}
    # Or just {id: vector}
    # User didn't specify schema for vectors, but usually we ingest text + vector together.
    # However, "legali_ready.json" has the text.
    # Let's create a file that merges them or just has vectors.
    # To be safe and RAG-ready, let's output a format that includes ID and Vector.
    
    output_data = []
    headers = {"model": MODEL_NAME, "dim": embeddings.shape[1], "count": len(chunks)}
    
    vectors = []
    for i, emb in enumerate(embeddings):
        vectors.append({
            "id": ids[i],
            "vector": emb.tolist()
        })
        
    final_payload = {
        "meta": headers,
        "data": vectors
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_payload, f)
        
    print(f"Saved {len(vectors)} vectors to {OUTPUT_FILE}")
    print(f"Dimensions: {headers['dim']}")

if __name__ == "__main__":
    generate_embeddings()
