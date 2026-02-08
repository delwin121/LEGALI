import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

def get_free_models():
    url = "https://openrouter.ai/api/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            all_models = data.get("data", [])
            
            # Filter for models containing ":free" or with pricing.id ending in free?
            # Usually strict ID ending in :free is the convention for the free endpoint alias.
            free_models = [m["id"] for m in all_models if ":free" in m["id"] or "free" in m["pricing"].get("id", "")]
            
            # Sort by context length or just alpha
            free_models.sort()
            
            print(f"Found {len(free_models)} free models:")
            for m in free_models:
                print(f"- {m}")
                
            return free_models
        else:
            print(f"Error fetching models: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

if __name__ == "__main__":
    get_free_models()
