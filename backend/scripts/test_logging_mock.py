from backend.app.rag import LegalRAG
import json
import logging

# MOCK SUBCLASS
class MockLegalRAG(LegalRAG):
    def generate_response(self, question, context_str):
        # Fake LLM response to test downstream logging & validation
        return "Murder is defined under Section 101 of the Bharatiya Nyaya Sanhita, 2023 [BNS-101-1]."

if __name__ == "__main__":
    print("Initializing Mock RAG...")
    rag = MockLegalRAG()
    
    print("Running Query...")
    result = rag.query("Test Query for Logging?")
    
    print("Query Complete.")
