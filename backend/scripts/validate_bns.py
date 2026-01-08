import json
import os

JSON_FILE = "backend/data/structured/bns.json"
TEXT_FILE = "backend/data/cleaned_text/bns.txt"

def validate_bns():
    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} missing.")
        return
    
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} clauses from JSON.")
    
    # Sort by number
    # Key is 'section_number' or 'clause_number'? 
    # Based on inspection: 'section_number'
    
    # Normalizing keys for check
    normalized = []
    for item in data:
        num = item.get('section_number') or item.get('clause_number')
        txt = item.get('text', '')
        normalized.append({'num': num, 'text': txt, 'raw': item})
        
    normalized.sort(key=lambda x: x['num'])
    
    # 1. Check Continuity
    missing_nums = []
    expected = 1
    for item in normalized:
        if item['num'] != expected:
            # Check if we skipped
            while expected < item['num']:
                missing_nums.append(expected)
                expected += 1
        expected += 1
        
    if missing_nums:
        print(f"FAILED: Missing clause numbers: {missing_nums}")
    else:
        print("SUCCESS: Clause numbers are continuous.")
        
    # 2. Check Empty Text
    empty_text = [x['num'] for x in normalized if not x['text'] or len(x['text'].strip()) < 10 or "MISSING_BODY" in x['text']]
    if empty_text:
        print(f"FAILED: Clauses with empty/suspicious text: {empty_text}")
    else:
        print("SUCCESS: No empty text fields found.")
        
    # 3. Check Source Match (Sample)
    # Load raw text
    try:
        with open(TEXT_FILE, 'r') as f:
            raw_text = f.read()
            
        print(f"Loaded raw text ({len(raw_text)} chars). Checking content matches...")
        
        matches = 0
        samples = normalized[::10] # Check every 10th
        for item in samples:
            # Take a chunk of text (first 50 chars ignoring special chars)
            snippet = item['text'][:50].split('(')[0].strip() 
            # If snippet is too short (e.g. just numbers), take more
            if len(snippet) < 10:
                snippet = item['text'][:50]
                
            # Allow some flexibility? 
            # Detailed check: search for the exact text string in bns.txt
            # normalize spaces
            clean_snippet = " ".join(snippet.split())
            if clean_snippet in " ".join(raw_text.split()): # Slow but fuzzy-safe
                matches += 1
            else:
                # Try simple check
                if snippet in raw_text:
                    matches += 1
                else:
                    # print(f"Warning: Text for Clause {item['num']} not found in source text. Snippet: '{snippet}'")
                    pass
                    
        print(f"Content sampling: {matches}/{len(samples)} matched source text.")
        
    except Exception as e:
        print(f"Could not verify against source text: {e}")

if __name__ == "__main__":
    validate_bns()
