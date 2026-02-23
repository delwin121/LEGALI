import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

def test_connection():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("FAIL: No API Key found in .env")
        return

    print(f"Testing Key: {api_key[:5]}...{api_key[-3:]}")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    try:
        # Simple cheap model call
        response = client.chat.completions.create(
            model="liquid/lfm-2.5-1.2b-instruct:free",
            messages=[{"role": "user", "content": "Ping"}],
            timeout=10
        )
        print("PASS: Connection Successful!")
        print(f"Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"FAIL: Connection Error: {e}")

if __name__ == "__main__":
    test_connection()
