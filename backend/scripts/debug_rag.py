
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.append("/home/aizen/LEGALI")

from backend.app.rag import LegalRAG

def test_rag():
    print("Initializing RAG...")
    try:
        rag = LegalRAG()
    except Exception as e:
        print(f"FAILED to initialize RAG: {e}")
        return

    query = "What is the punishment for murder under BNS?"
    print(f"\nQuerying: {query}")
    
    try:
        result = rag.query(query)
        print("\n--- RESULT ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"FAILED during query: {e}")

if __name__ == "__main__":
    test_rag()
