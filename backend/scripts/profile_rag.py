
import sys
import time
import json
sys.path.append("/home/aizen/LEGALI")
from backend.app.rag import LegalRAG

def profile():
    print("Initializing...")
    start = time.time()
    rag = LegalRAG()
    print(f"Init Time: {time.time() - start:.2f}s")

    query = "What is the punishment for murder?"
    print(f"\nProfiling Query: {query}")
    
    # Measure Retrieval
    t0 = time.time()
    retrieval = rag.retrieve(query)
    t1 = time.time()
    print(f"Retrieval Time: {t1 - t0:.2f}s")
    
    ids = retrieval['ids'][0]
    if not ids:
        print("No documents retrieved.")
        return

    # Build Context
    context_parts = []
    docs = retrieval['documents'][0]
    metas = retrieval['metadatas'][0]
    for i in range(len(ids)):
        context_parts.append(f"SOURCE_ID: [{ids[i]}]\nTEXT:\n{docs[i]}\n")
    context_str = "\n---\n".join(context_parts)
    print(f"Context Length: {len(context_str)} chars")

    # Measure Generation
    t2 = time.time()
    # Direct call to generate_response to skip overhead
    answer = rag.generate_response(query, context_str)
    t3 = time.time()
    print(f"Generation Time: {t3 - t2:.2f}s")
    
    print(f"\nTotal Query Time: {t3 - t0:.2f}s")

if __name__ == "__main__":
    profile()
