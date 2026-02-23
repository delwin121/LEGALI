import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.rag import LegalRAG

def test_backend_logic():
    print("Initializing LegalRAG...")
    try:
        rag = LegalRAG()
    except Exception as e:
        print(f"FAILED: Could not initialize RAG: {e}")
        return

    query = "What is the punishment for murder?"
    print(f"\nRunning Query: {query}")
    
    try:
        result = rag.query(query)
    except Exception as e:
        print(f"FAILED: Query execution failed: {e}")
        return

    # print(json.dumps(result, indent=2))

    # Benchmark 1: Structure Keys
    required_keys = ['answer', 'citations', 'suggested_questions']
    missing_keys = [k for k in required_keys if k not in result]
    
    if missing_keys:
        print(f"FAILED: Missing keys in response: {missing_keys}")
    else:
        print("PASS: JSON Structure verified.")

    # Benchmark 2: Answer Length (Executive Summary)
    answer_words = len(result['answer'].split())
    print(f"Answer Word Count: {answer_words}")
    
    if answer_words < 150:
        print("PASS: Executive Summary constraint met (<150 words).")
    else:
        print(f"WARNING: Answer might be too long ({answer_words} words).")

    # Benchmark 3: Citations Structure
    citations = result.get('citations', [])
    if isinstance(citations, list) and len(citations) > 0:
        first_cit = citations[0]
        if all(k in first_cit for k in ['act', 'section', 'chapter']):
            print(f"PASS: Text-free Citations validated ({len(citations)} sources).")
        else:
            print(f"FAILED: Invalid Citation format: {first_cit}")
    else:
        print("WARNING: No citations returned (Check retrieval gate).")

    # Benchmark 4: Suggested Questions
    questions = result.get('suggested_questions', [])
    if len(questions) == 3:
        print(f"PASS: Exactly 3 Suggested Questions generated.")
    else:
        print(f"WARNING: Generated {len(questions)} suggested questions (Expected 3).")

if __name__ == "__main__":
    test_backend_logic()
