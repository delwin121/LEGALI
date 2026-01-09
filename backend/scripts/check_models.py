import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

print("Fetching models...")
try:
    models = client.models.list()
    found = False
    print("\n--- Available Llama Models ---")
    for m in models.data:
        if "llama" in m.id.lower() or "free" in m.id.lower():
            print(m.id)
            if "405b" in m.id:
                found = True
    
    if not found:
        print("\n⚠️ Requested 405B model not found in list.")
except Exception as e:
    print(f"Error fetching models: {e}")
