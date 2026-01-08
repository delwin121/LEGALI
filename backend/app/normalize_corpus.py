import json
import re
from pathlib import Path

# Paths
DATA_DIR = Path("backend/data/structured")
OUTPUT_FILE = Path("backend/data/final/legali_corpus.json")

def normalize():
    corpus = []
    
    # 1. BNS
    # Keys: chapter, section_number, section_title, text
    print("Processing BNS...")
    with open(DATA_DIR / "bns.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            corpus.append({
                "act": "BNS",
                "chapter": item.get('chapter', '').strip(),
                "number": item.get('section_number') or item.get('clause_number'),
                "title": item.get('section_title', '').strip(),
                "text": item.get('text', '').strip(),
                "source": "official"
            })

    # 2. BNSS
    # Keys: chapter, clause_number, clause_title, text
    print("Processing BNSS...")
    with open(DATA_DIR / "bnss.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
             corpus.append({
                "act": "BNSS",
                "chapter": item.get('chapter', '').strip(),
                "number": item.get('clause_number'),
                "title": item.get('clause_title', '').strip(),
                "text": item.get('text', '').strip(),
                "source": "official"
            })

    # 3. BSA
    # Keys: chapter, section_number, section_title, text
    # (Checking if it uses section_number based on previous task)
    print("Processing BSA...")
    with open(DATA_DIR / "bsa.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
             corpus.append({
                "act": "BSA",
                "chapter": item.get('chapter', '').strip(),
                "number": item.get('section_number'),
                "title": item.get('section_title', '').strip(),
                "text": item.get('text', '').strip(),
                "source": "official"
            })

    # Validation
    print(f"Total Corpus Size: {len(corpus)} entries")
    
    # 4. Global Cleanup
    print("Performing global cleanup...")
    
    # Regex for Chapter Header at end of text
    # Matches "CHAPTER" followed by Roman Numeral, then optional text, at end of string
    # We want to match greedy until end.
    re_chapter_tail = re.compile(r'\n?\s*CHAPTER\s+[IVXLCDM]+\s+[A-Z\s]+$')
    
    # Regex for Title Residue at start
    # Matches typically lowercase word segments ending in dash
    # e.g. "convict.—"
    # residue usually ends with dot-dash or just dash
    # \u2013 = en-dash, \u2014 = em-dash
    re_title_residue = re.compile(r'^[a-z\s]+\.?[\-\u2013\u2014]+\s*')
    
    cleaned_count = 0
    cleaned_residue_count = 0
    cleaned_chapter_count = 0
    
    for item in corpus:
        text = item['text']
        original = text
        
        # 4a. Statement of Objects
        if "STATEMENT OF OBJECTS AND REASONS" in text:
            idx = text.find("STATEMENT OF OBJECTS AND REASONS")
            text = text[:idx].strip()
            
        # 4b. Chapter Headers at end
        # Sometimes it's just "CHAPTER II". Note BNS-3 text: "...homicide.\nCHAPTER II OF PUNISHMENTS"
        # We try to remove it.
        # We repeat in case multiple? No, usually one.
        match_chap = re_chapter_tail.search(text)
        if match_chap:
            text = text[:match_chap.start()].strip()
            cleaned_chapter_count += 1
            
        # 4c. Title Residue
        # Check if start matches lowercase residue
        match_res = re_title_residue.match(text)
        if match_res:
            # Dangerous if genuine text starts with lowercase?
            # Legal text should start with Capital or (1).
            # If it starts with "convict.—", it's residue.
            # If it starts with "provided that...", 'p' is lowercase. But usually follows punctuation.
            # We assume corpus text maps to a full section/clause which should start capitalized.
            text = text[match_res.end():].strip()
            cleaned_residue_count += 1
            
        if text != original:
            item['text'] = text
            cleaned_count += 1
            
    print(f"Cleaned {cleaned_count} entries ({cleaned_chapter_count} chapters, {cleaned_residue_count} residues).")

    # Check for None values

    # Check for None values
    for i, item in enumerate(corpus):
        if item['number'] is None:
            print(f"Error: Item at index {i} in {item['act']} has no number.")
        if not item['text']:
             # If text became empty after cleaning?
            print(f"Error: Item at index {i} in {item['act']} has empty text after cleaning.")
            
    # Write
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
        
    print(f"Saved normalized corpus to {OUTPUT_FILE}")

if __name__ == "__main__":
    normalize()
