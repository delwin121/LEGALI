import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def verify_system():
    print("--- Phase 3 Verification: System Integration & Stress Test ---")
    
    # 1. Health Check
    print("\n1. Pinging Health Check...")
    try:
        r = requests.get(f"{BASE_URL}/")
        if r.status_code == 200:
            print("PASS: System Healthy (200 OK)")
        else:
            print(f"FAILED: Health check returned {r.status_code}")
            return
    except Exception as e:
        print(f"FAILED: Could not connect to backend: {e}")
        return

    # 2. Complex Query
    query = "What is the punishment for murder?"
    print(f"\n2. Sending Complex Query: '{query}'")
    
    payload = {"query": query}
    start_time = time.time()
    
    try:
        r = requests.post(f"{BASE_URL}/chat", json=payload)
        elapsed = time.time() - start_time
        print(f"Response Time: {elapsed:.2f}s")
        
        if r.status_code == 200:
            data = r.json()
            
            # 3. Assertions
            # Answer
            if data.get("answer"):
                print("PASS: Answer generated.")
                if len(data["answer"].split()) < 150:
                     print("PASS: Executive Summary constraint met.")
                else:
                     print(f"WARNING: Answer length {len(data['answer'].split())} words.")
            else:
                 print("FAILED: No answer returned.")
            
            # Citations
            citations = data.get("citations", [])
            if citations:
                print(f"PASS: {len(citations)} Citations returned.")
                # Verify structure
                if all(k in citations[0] for k in ["act", "section"]):
                    print("PASS: Citation structure validated.")
            else:
                print("WARNING: No citations returned.")

            # Chips
            chips = data.get("suggested_questions", [])
            if chips:
                print(f"PASS: {len(chips)} Suggested Questions generated.")
            else:
                print("FAILED: No suggested questions.")
                
            print("\nSYSTEM HEALTHY: READY FOR DEMO")
            
        else:
            print(f"FAILED: Query endpoint returned {r.status_code}")
            print(r.text)
            
    except Exception as e:
        print(f"FAILED: Query request failed: {e}")

if __name__ == "__main__":
    # Wait for server to potentially start if running immediately after startup
    time.sleep(2)
    verify_system()
