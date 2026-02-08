
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    # Use a dummy key if none (though it might fail auth)
    # The user logs implied they have a key (hitting limits or 404s).
    print("No API Key found")
    exit(1)

models_to_test = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free"
]

print(f"Testing models with key ending in ...{api_key[-4:]}")

for model in models_to_test:
    print(f"\nTesting {model}...")
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
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
