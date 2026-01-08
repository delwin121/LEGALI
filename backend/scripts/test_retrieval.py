import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Config
DB_DIR = Path("backend/data/chroma_db")
COLLECTION_NAME = "legali_corpus"
MODEL_NAME = "BAAI/bge-base-en-v1.5"

QUERIES = [
    "What is murder under BNS?",
    "Procedure for arrest without warrant",
    "Maintenance of wife under BNSS"
]

def test():
    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"Connecting to DB at {DB_DIR}...")
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    
    print("\n=== RUNNING BENCHMARK QUERIES ===\n")
    
    for q in QUERIES:
        print(f"Query: {q}")
        
        # BGE-v1.5 Instruction for Retrieval
        # "Represent this sentence for searching relevant passages: "
        instruction = "Represent this sentence for searching relevant passages: "
        query_text = instruction + q
        
        # Embed
        query_vec = model.encode([query_text], normalize_embeddings=True).tolist()
        
        # Search
        results = collection.query(
            query_embeddings=query_vec,
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )
        
        # Display
        ids = results['ids'][0]
        docs = results['documents'][0]
        metas = results['metadatas'][0]
        dists = results['distances'][0]
        
        for i in range(len(ids)):
            print(f"  [{i+1}] ID: {ids[i]} (Dist: {dists[i]:.4f})")
            print(f"      Title: {metas[i]['title']}")
            snippet = docs[i].replace('\n', ' ')[:150]
            print(f"      Text: {snippet}...")
            print("-" * 40)
        print("\n")

if __name__ == "__main__":
    test()
