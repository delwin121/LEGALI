import sys
from pathlib import Path
import json
import time

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.rag import LegalRAG

def test_rag():
    print("Initializing LegalRAG...")
    rag = LegalRAG()
    
    query = "What is the punishment for murder?"
    print(f"\nQuerying: {query}")
    
    start_time = time.time()
    result = rag.query(query)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"\nResponse Time: {duration:.2f} seconds")
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    # Validation
    if "error" in result:
        print("\n❌ Test Failed: Error in response")
        return
        
    if not result.get("answer"):
        print("\n❌ Test Failed: Empty answer")
        return
        
    if not result.get("citations"):
        print("\n❌ Test Failed: No citations")
        return
        
    print("\n✅ Test Passed: Valid response with citations")

if __name__ == "__main__":
    test_rag()
