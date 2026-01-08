import json
import re
import unicodedata
from pathlib import Path

INPUT_FILE = Path("backend/data/final/legali_chunks.json")
OUTPUT_FILE = Path("backend/data/final/legali_ready.json")

def is_control_char(char):
    # Keep newlines and tabs, remove others (like null, backspace, etc)
    if char in ('\n', '\t', '\r'):
        return False
    return unicodedata.category(char).startswith("C")

def clean_text(text):
    # 1. Normalize unicode (NFKC)
    text = unicodedata.normalize('NFKC', text)
    
    # 2. Remove control characters
    text = "".join(c for c in text if not is_control_char(c))
    
    # 3. Check for Page headers/footers
    # Regex for "Page <Num>" on a line by itself
    text = re.sub(r'(?m)^\s*Page\s+\d+\s*$', '', text)
    # Regex for just digits on a line by itself? (Page numbers sometimes)
    # But be careful about "(1)"
    # A distinct page number usually is centered or at edges. 
    # Let's remove lines that are just digits greater than length 3 (unlikely to be a list item "1.")?
    # Or just lines matching `^\d+$` ? 
    # BNS sections go up to 350. So `350` on a line is ambiguous.
    # However, strict instructions say "No page numbers".
    # We will assume parsing already avoided most, but let's scrub explicit "Page X".
    
    # 4. Check for ARRANGEMENT OF SECTIONS
    # This might have slipped in?
    if "ARRANGEMENT OF SECTIONS" in text or "ARRANGEMENT OF CLAUSES" in text:
        # If it's the title of the chunk? Or inside body?
        # If inside body, it's likely trash.
        text = text.replace("ARRANGEMENT OF SECTIONS", "")
        text = text.replace("ARRANGEMENT OF CLAUSES", "")
        
    return text.strip()

def finalize():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} missing.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    print(f"Loaded {len(chunks)} chunks. Cleaning...")
    
    cleaned_chunks = []
    skipped_count = 0
    
    for chunk in chunks:
        original_text = chunk['text']
        cleaned_text = clean_text(original_text)
        
        # If text became empty (unlikely), skip
        if not cleaned_text:
            print(f"Warning: Chunk {chunk['id']} became empty after cleaning. Skipping.")
            skipped_count += 1
            continue
            
        # Update text
        chunk['text'] = cleaned_text
        cleaned_chunks.append(chunk)

    # Validate output
    # Ensure UTF-8 compliancy is implicit by using json.dump with ensure_ascii=False
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned_chunks, f, indent=2, ensure_ascii=False)
        
    print(f"Finalized {len(cleaned_chunks)} chunks.")
    print(f"Skipped {skipped_count} empty chunks.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    finalize()
