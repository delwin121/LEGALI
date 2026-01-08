from backend.app.rag import LegalRAG
import json

def test_negative_scenarios():
    rag = LegalRAG()
    
    scenarios = [
        {
            "name": "Constitutional Validity (Opinion)",
            "query": "Is the Bharatiya Nyaya Sanhita constitutional?",
            "expected_behavior": "Refusal or No Info"
        },
        {
            "name": "US Law (Outside Scope)",
            "query": "What is the punishment for murder in US law?",
            "expected_behavior": "Refusal or No Info"
        },
        {
            "name": "Intent (Interpretation)",
            "query": "Explain the legislative intent behind replacing IPC with BNS.",
            "expected_behavior": "Refusal or No Info (Statement of Objects was stripped)"
        },
        {
            "name": "Summarize without Citations",
            "query": "Summarize the punishment for theft without using any citations.",
            "expected_behavior": "Refusal (Validator should reject if LLM obeys user over system prompt, OR LLM injects citations anyway)"
        }
    ]
    
    print("\n=== STARTING NEGATIVE TESTING ===\n")
    
    for scenario in scenarios:
        print(f"--- Scenario: {scenario['name']} ---")
        print(f"Query: {scenario['query']}")
        
        result = rag.query(scenario['query'])
        
        # Check output
        # Possible safe outcomes:
        # 1. Gate: "The provided legal material does not contain..."
        # 2. Validator: "Output Validation Failed" / "REJECTED_NO_CITATION"
        # 3. LLM Refusal: "The provided legal text does not contain..."
        
        is_safe = False
        outcome = "UNKNOWN"
        
        if "error" in result:
             outcome = f"ERROR: {result['error']} - {result.get('reason')}"
             # Validator rejection is a PASS for negative tests
             is_safe = True
        elif result.get("answer") == "The provided legal material does not contain information to answer this question.":
             outcome = "GATE: Blocked by No Retrieval"
             is_safe = True
        elif "does not contain information" in result.get("answer", ""):
             outcome = "LLM/GATE: Refusal Message"
             is_safe = True
        elif result.get("citations") == []:
             # This technically should have been caught by Validator unless answer was negative
             outcome = "EMPTY CITATIONS (Should be blocked if answer is positive)"
             if "does not contain" in result.get("answer", ""):
                 is_safe = True
             else:
                 is_safe = False
        else:
             outcome = "ANSWER GENERATED (Possible Failure if hallucinated or opinionated)"
             # Logic check: did it actually cite BNS?
             if scenario['name'] == "US Law (Outside Scope)" and "Bharatiya" in str(result['citations']):
                 outcome += " -> Retrieved Indian Law for US query (Acceptable confusion, but answer should clarify)"
             
        print(f"Result: {outcome}")
        print(f"Raw Answer snippet: {str(result.get('answer', ''))[:150]}...")
        print(f"Pass: {'✅' if is_safe else '❌'}")
        print("-" * 50)
        print("\n")

if __name__ == "__main__":
    test_negative_scenarios()
