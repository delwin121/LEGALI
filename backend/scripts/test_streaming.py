import requests
import json
import uuid

def test_streaming():
    url = "http://localhost:8000/chat/stream"
    session_id = str(uuid.uuid4())
    payload = {
        "query": "What is the punishment for murder under BNS?",
        "session_id": session_id
    }
    
    print(f"Testing Streaming Endpoint: {url}")
    print(f"Session ID: {session_id}")
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code != 200:
                print(f"FAILED: Status Code {response.status_code}")
                print(response.text)
                return

            print("--- STREAM START ---")
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]
                        try:
                            data = json.loads(json_str)
                            if data['type'] == 'content':
                                print(data['data'], end="", flush=True)
                            elif data['type'] == 'metadata':
                                print("\n\n--- METADATA ---")
                                print(json.dumps(data, indent=2))
                            elif data['type'] == 'error':
                                print(f"\nERROR: {data['data']}")
                        except Exception as e:
                            print(f"\n[Parse Error: {e}] Line: {decoded_line}")
            print("\n--- STREAM END ---")
            
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    test_streaming()
