
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

models_to_test = [
    "gryphe/mythomax-l2-13b:free",
    "openchat/openchat-7:free",
    "undi95/toppy-m-7b:free",
    "google/gemma-2-9b-it:free"
]

print(f"Testing models with key ending in ...{api_key[-4:]}")

for model in models_to_test:
    print(f"\nTesting {model}...")
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "LEGALI"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=10
        )
        if resp.status_code == 200:
            print(f"SUCCESS: {model}")
        else:
            print(f"FAILED: {model} - {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"ERROR: {model} - {e}")
