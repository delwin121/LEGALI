import chromadb
import json
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Config
DATA_DIR = Path("backend/data/final")
DB_DIR = Path("backend/data/chroma_db")
COLLECTION_NAME = "legali_corpus"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

def ingest():
    print(f"Initializing ChromaDB in {DB_DIR}...")
    client = chromadb.PersistentClient(path=str(DB_DIR))
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 1. Load All Chunks
    print("Scanning for chunk files...")
    chunks = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith("_ready.json") or filename.endswith("_ready_v2.json"):
            filepath = DATA_DIR / filename
            print(f"Loading chunks from: {filename}")
            with open(filepath, 'r', encoding='utf-8') as f:
                chunks.extend(json.load(f))
                
    # 2. Load Pre-Computed Vectors (If Available)
    vec_map = {}
    print("Scanning for vector caches...")
    for filename in os.listdir(DATA_DIR):
        if "vectors" in filename and filename.endswith(".json"):
            filepath = DATA_DIR / filename
            print(f"Loading vector cache from: {filename}")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    vectors_data = json.load(f)
                    if 'data' in vectors_data:
                        for item in vectors_data['data']:
                            vec_map[item['id']] = item['vector']
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                
    print(f"Total Chunks Loaded: {len(chunks)}")
    print(f"Cached Vectors Found: {len(vec_map)}")
    
    # 3. Separate Cached vs Missing Vectors
    ids = []
    documents = []
    embeddings = []
    metadatas = []
    
    missing_chunks = []
    
    for chunk in chunks:
        cid = chunk['id']
        vector = vec_map.get(cid)
        
        meta = {
            "act": str(chunk.get('act', '')),
            "chapter": str(chunk.get('chapter', '')),
            "section_number": str(chunk.get('number', '')),
            "title": str(chunk.get('title', '')),
            "chunk_index": int(chunk.get('chunk_index', 0))
        }
        
        if vector is None:
            missing_chunks.append((cid, chunk['text'], meta))
        else:
            ids.append(cid)
            documents.append(chunk['text'])
            embeddings.append(vector)
            metadatas.append(meta)
            
    # 4. Dynamically Encode Missing Chunks
    if missing_chunks:
        print(f"Generating embeddings dynamically for {len(missing_chunks)} unseen chunks...")
        embedder = SentenceTransformer(EMBEDDING_MODEL)
        
        texts_to_encode = [f"Represent this sentence for searching relevant passages: {c[1]}" for c in missing_chunks]
        new_vecs = embedder.encode(texts_to_encode, normalize_embeddings=True, show_progress_bar=True).tolist()
        
        for i, (cid, text, meta) in enumerate(missing_chunks):
            ids.append(cid)
            documents.append(text)
            embeddings.append(new_vecs[i])
            metadatas.append(meta)
            
    # 5. Upsert to ChromaDB in Batches
    if not ids:
        print("No data to ingest.")
        return
        
    batch_size = 100
    total = len(ids)
    print(f"Executing batch up-sert for {total} elements...")
    
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        print(f"Upserting batch {i} -> {end}...")
        try:
            collection.upsert(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )
        except Exception as e:
            print(f"Batch Upsert Error on {i}->{end}: {e}")
            
    count = collection.count()
    print(f"\nIngestion Complete! Vector Database contains [{count}] items.")

if __name__ == "__main__":
    ingest()
