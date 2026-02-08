
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from backend.app.rag import LegalRAG

def test_query():
    rag = LegalRAG()
    question = "punishment for murder"
    print(f"Querying: {question}")
    result = rag.query(question)
    print("--- RESULT ---")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_query()
