import chromadb
import json
import os
from pathlib import Path

# Config
DATA_DIR = Path("backend/data/final")
CHUNKS_FILE = DATA_DIR / "legali_ready_v2.json"
VECTORS_FILE = DATA_DIR / "legali_vectors_v2.json"
DB_DIR = Path("backend/data/chroma_db")
COLLECTION_NAME = "legali_corpus"

def ingest():
    # 1. Validation
    if not CHUNKS_FILE.exists() or not VECTORS_FILE.exists():
        print("Error: Missing input files (chunks or vectors).")
        return

    print(f"Initializing ChromaDB in {DB_DIR}...")
    # Initialize persistent client
    client = chromadb.PersistentClient(path=str(DB_DIR))
    
    # Get or create collection
    # We use cosine similarity space (Metadata says "model encoded").
    # BGE uses cosine.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 2. Load Data
    print("Loading data...")
    with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    with open(VECTORS_FILE, 'r', encoding='utf-8') as f:
        vectors_data = json.load(f)
        
    # Map vectors by ID
    # vectors_data = { meta: ..., data: [ {id, vector}, ... ] }
    vec_map = {item['id']: item['vector'] for item in vectors_data['data']}
    
    print(f"Loaded {len(chunks)} chunks and {len(vec_map)} vectors.")
    
    # 3. Prepare Batch
    ids = []
    documents = []
    embeddings = []
    metadatas = []
    
    missing_vecs = 0
    
    for chunk in chunks:
        cid = chunk['id']
        vector = vec_map.get(cid)
        
        if vector is None:
            missing_vecs += 1
            print(f"Warning: No vector found for {cid}")
            continue
            
        ids.append(cid)
        documents.append(chunk['text'])
        embeddings.append(vector)
        
        # Metadata
        # We store structure info for filtering
        meta = {
            "act": chunk['act'],
            "chapter": chunk['chapter'],
            "section_number": chunk['number'], # integer
            "title": chunk['title'],
            "chunk_index": chunk['chunk_index']
        }
        metadatas.append(meta)
        
    if missing_vecs > 0:
        print(f"Skipping {missing_vecs} chunks due to missing vectors.")
        
    # 4. Upsert to DB
    # Chroma handles batching, but for 1200 it's fine to do in one go or blocks of 100.
    # Let's do batches of 100 to be safe/show progress.
    batch_size = 100
    total = len(ids)
    print(f"Ingesting {total} items into ChromaDB...")
    
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        print(f"Upserting batch {i} to {end}...")
        collection.upsert(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end]
        )
        
    print("Ingestion complete.")
    print(f"DB persisted at: {DB_DIR}")
    
    # Verify count
    count = collection.count()
    print(f"Total documents in collection: {count}")

if __name__ == "__main__":
    ingest()
