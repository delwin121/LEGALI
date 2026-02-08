import requests
import json
import sys

URL = "http://localhost:8000/query"
QUERY = {"query": "punishment for murder"}

try:
    print(f"Sending POST request to {URL}...")
    response = requests.post(URL, json=QUERY)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")

    if response.status_code == 503:
        data = response.json()
        status = data.get("detail", {}).get("status")
        if status in ["LLM_RATE_LIMIT", "LLM_PROVIDER_ERROR", "LLM_QUOTA_EXCEEDED"]:
            print(f"✅ Verification PASSED: Server returned 503 with status {status}")
            sys.exit(0)
        else:
            print(f"❌ Verification FAILED: Status is 503 but unexpected status {status}")
            sys.exit(1)
    elif response.status_code == 200:
        print("❌ Verification FAILED: Server returned 200 OK (Unexpected success, maybe rate limit cleared?).")
        sys.exit(1)
    else:
        print(f"❌ Verification FAILED: Unexpected status code {response.status_code}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Verification FAILED: Exception occurred: {e}")
    sys.exit(1)
