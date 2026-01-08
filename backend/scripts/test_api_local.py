from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.api import app

client = TestClient(app)

def test_health():
    print("Testing / (Health Check)...")
    response = client.get("/")
    assert response.status_code == 200
    print(f"Response: {response.json()}")
    assert response.json()["status"] == "online"
    print("Health check passed!")

def test_query():
    print("\nTesting /query (RAG)...")
    # Using a simple query that should retrieve something or at least return a valid response
    payload = {"query": "What is the punishment for murder?"}
    response = client.post("/query", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        print(f"Answer: {data.get('answer')}")
        print(f"Citations: {len(data.get('citations', []))}")
    else:
        print(f"Failed: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    print("Starting API Tests...")
    test_health()
    test_query()
