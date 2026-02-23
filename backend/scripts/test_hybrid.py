import sys
import os
sys.path.append(os.getcwd())
try:
    from backend.app.rag import LegalRAG
    print("SUCCESS: Imported LegalRAG")
except ImportError as e:
    print(f"FAILURE: Could not import LegalRAG: {e}")
    sys.exit(1)

def test_rag():
    print("Initializing RAG System...")
    rag = LegalRAG()
    
    if rag.bm25 is None:
        print("WARNING: BM25 not initialized (Fallback mode active?)")
    else:
        print("SUCCESS: BM25 initialized.")

    query = "Section 302"
    print(f"Querying: '{query}'...")
    try:
        result = rag.query(query)
        print("Query returned result.")
    except Exception as e:
        print(f"FAILURE: Query crashed: {e}")
        return

    answer = result.get('answer', '')
    citations = result.get('citations', [])
    
    print("-" * 40)
    print(f"Answer Preview: {answer[:100]}...")
    print(f"Citations: {citations}")
    print("-" * 40)

    # Verification Logic
    # 1. Check for Section 302 text or citation
    found_302 = False
    for cit in citations:
        # Check section number string, might be "302"
        if "302" in str(cit.get('section', '')):
            found_302 = True
            break
    
    if found_302:
        print("VERIFICATION PASSED: Section 302 found in citations.")
    else:
        # Fallback check in answer text
        if "Punishment for murder" in answer or "death" in answer.lower():
             print("VERIFICATION WARNING: Section 302 not in citations but answer seems relevant.")
        else:
             print("VERIFICATION FAILED: Section 302 not found in citations or answer.")

if __name__ == "__main__":
    test_rag()
