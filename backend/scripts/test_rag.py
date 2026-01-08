from backend.app.rag import LegalRAG
import time

QUERIES = [
    "What is murder under BNS?",
    "Procedure for arrest without warrant",
    "Maintenance of wife under BNSS"
]

def benchmark():
    print("Initializing RAG System...")
    rag = LegalRAG()
    
    print("\n=== STARTING RAG BENCHMARK ===\n")
    
    for i, q in enumerate(QUERIES, 1):
        print(f"Query {i}: {q}")
        start_time = time.time()
        
        result = rag.query(q)
        
        elapsed = time.time() - start_time
        
        print(f"Time: {elapsed:.2f}s")
        print(f"Answer:\n{result['answer']}")
        print(f"Sources Used: {result['sources']}")
        print("-" * 50)
        print("\n")

if __name__ == "__main__":
    benchmark()
