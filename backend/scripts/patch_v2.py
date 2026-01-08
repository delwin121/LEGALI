import json
from pathlib import Path

INPUT_FILE = Path("backend/data/final/legali_ready.json")
OUTPUT_FILE = Path("backend/data/final/legali_ready_v2.json")

def patch():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    print(f"Loaded {len(chunks)} chunks.")
    
    new_chunks = []
    
    # Track latest index for renumbering
    # Map (Act, Number) -> max_index
    max_indices = {}
    
    # First pass: Identify max indices for legitimate chunks
    # But checking collision is hard if we don't know which one comes first.
    # The JSON is ordered usually.
    
    # Specific Fixes:
    # BNS-5: Remove the one starting with "related Parliamentary"
    # BNS-63: Renumber the second occurrences.
    
    for chunk in chunks:
        cid = chunk['id']
        text = chunk['text']
        
        # BNS-5 Check
        if chunk['act'] == 'BNS' and chunk['number'] == 5:
            if "Parliamentary Standing Committee" in text:
                print(f"Dropping trash chunk: {cid} (Parliamentary info)")
                continue
        
        # BNS-63 Check (or generic renumbering)
        # We need to ensure unique IDs.
        # We can just re-generate IDs on the fly?
        # "Chunking rules: chunk_index starts at 1".
        # If we have multiple input sections for "BNS 63", we effectively merge them into one sequence.
        
        key = (chunk['act'], chunk['number'])
        current_idx = max_indices.get(key, 0) + 1
        max_indices[key] = current_idx
        
        # Check if ID needs update
        expected_id = f"{chunk['act']}-{chunk['number']}-{current_idx}"
        
        if cid != expected_id:
            print(f"Renumbering {cid} -> {expected_id}")
            chunk['id'] = expected_id
            chunk['chunk_index'] = current_idx
            
        new_chunks.append(chunk)
        
    print(f"Patched {len(new_chunks)} chunks.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_chunks, f, indent=2, ensure_ascii=False)
        
    print(f"Saved V2 to {OUTPUT_FILE}")

if __name__ == "__main__":
    patch()
