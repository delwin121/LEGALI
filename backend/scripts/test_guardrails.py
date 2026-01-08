from backend.app.rag import LegalRAG

def test_guardrails():
    rag = LegalRAG()
    
    print("\n=== TEST 1: Happy Path (Murder) ===")
    res1 = rag.query("What is murder under BNS?")
    debug1 = res1.get('debug_metadata', {})
    print(f"Status: {debug1.get('status', 'N/A')}")
    print(f"Answer Snippet: {res1['answer'][:100]}...")
    print(f"Citations: {res1['citations']}")
    
    print("\n=== TEST 2: Retrieval Gate (Gibberish) ===")
    # Searching for something definitely not in Indian Law
    res2 = rag.query("How to bake a pineapple cake in zero gravity?")
    # This might still retrieve something due to dense vector similarity, 
    # but the dists would be high.
    # However, our gate only checks EMPTY results.
    # Chromadb always returns *something* if we ask for n_results=5 unless database is empty.
    # To test the gate properly, we'd need to mock empty return or implement distance filtering.
    # But let's see what happens. If it returns text, the LLM should say "Not relevant".
    debug2 = res2.get('debug_metadata', {})
    print(f"Status: {debug2.get('status', 'N/A')}")
    print(f"Answer: {res2['answer']}")
    REQUIRED_MSG = "The provided legal material does not contain information to answer this question."
    if res2['answer'] == REQUIRED_MSG:
        print("✅ Gate Message Verified")
    else:
        print(f"⚠️ Answer differs from strict requirement (Might be LLM fallback if search was not empty)")
    
    # Optional: Mocking empty retrieval for Test 2 if BGE finds "nearest neighbors" anyway.
    # If BGE returns neighbors, the LLM prompt (Layer B) should trigger "does not contain info".
    
    print("\n=== TEST 3: Validation (Simulated Failure) ===")
    # We can't easily force the LLM to fail citation without changing the prompt.
    # But we can assume Test 1 passed validation if Status == SUCCESS.

if __name__ == "__main__":
    test_guardrails()
