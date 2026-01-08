import json
import re
from pathlib import Path

INPUT_FILE = Path("backend/data/final/legali_corpus.json")
OUTPUT_FILE = Path("backend/data/final/legali_chunks.json")

# TARGET: 400-700 tokens
# Heuristic: 1 token ~= 4 chars
MIN_TOKENS = 400
MAX_TOKENS = 700
CHARS_PER_TOKEN = 4

MIN_CHARS = MIN_TOKENS * CHARS_PER_TOKEN
MAX_CHARS = MAX_TOKENS * CHARS_PER_TOKEN

def count_tokens(text):
    return len(text) // CHARS_PER_TOKEN

def split_into_sentences(text):
    # Basic sentence splitter
    # Look for [.!?] followed by space and capital letter or digit (start of next sentence)
    # But legal text has abbreviations "Sec.", "No." etc.
    # We'll use a slightly robust regex but rely on recombining.
    return re.split(r'(?<=[.!?])\s+(?=[A-Z0-9\(])', text)

def recursive_split(text):
    """
    Splits text into atomic units based on legal structure boundaries.
    """
    # Base case
    if count_tokens(text) <= MAX_TOKENS:
        return [text]

    # Level 1: Split by Newlines
    if '\n' in text:
        parts = text.split('\n')
        parts = [p.strip() for p in parts if p.strip()]
        
        # If splitting by newline didn't change anything (e.g. single line), proceed to Level 2
        if len(parts) > 1 or (len(parts) == 1 and parts[0] != text):
            final_atoms = []
            for p in parts:
                final_atoms.extend(recursive_split(p))
            return final_atoms

    # Level 2: Split by Sub-structures
    # Usage of capturing group to keep the delimiter
    # Delimiters: (1), (2), (a), (b), Explanation, Illustration
    # We want the delimiter to start the NEW chunk.
    # regex: ( (?:Explanation|Illustration|\(\d+\)|\([a-z]\)) )
    # Note: \(\d+\) matches (1), (10). \([a-z]\) matches (a).
    
    delimiters = r'(Explanation|Illustration|\(\d+\)|\([a-z]\))'
    # Check if text actually contains these before splitting
    if re.search(delimiters, text):
        parts = re.split(delimiters, text)
        # Result: [Pre, Delim1, Post1, Delim2, Post2...]
        # We want to combine Delim + Post
        
        recombined = []
        current_atom = ""
        
        # The first part is 'Pre' (before first delim). Might be empty or intro text.
        if parts[0].strip():
            recombined.append(parts[0].strip())
            
        # Iterate pairs
        for i in range(1, len(parts), 2):
            delim = parts[i]
            content = parts[i+1] if i+1 < len(parts) else ""
            
            # Form block
            block = (delim + content).strip()
            if block:
                recombined.append(block)
                
        # Critical check: Did we actually split?
        # If recombined has 1 element and it's equal to text, we failed to split effectively -> infinite loop.
        if len(recombined) > 1 or (len(recombined) == 1 and len(recombined[0]) < len(text)):
            final_atoms = []
            for p in recombined:
                final_atoms.extend(recursive_split(p))
            return final_atoms

    # Level 3: Split by Sentences
    sentences = split_into_sentences(text)
    if len(sentences) > 1:
        # Check progress
        if len(sentences) > 1:
             return sentences
        
    return [text]

def merge_chunks(atoms):
    """
    Merges atomic text units into chunks of valid size (400-700 tokens).
    """
    chunks = []
    current_chunk = ""
    
    for atom in atoms:
        # Check size if we add this atom
        proposed_text = (current_chunk + "\n" + atom).strip()
        proposed_size = count_tokens(proposed_text)
        
        if proposed_size > MAX_TOKENS:
            # Current chunk is full-ish.
            # But wait, if current_chunk is EMPTY (atom itself is > MAX), we force add it.
            if not current_chunk:
                chunks.append(atom)
            else:
                chunks.append(current_chunk)
                current_chunk = atom
        else:
            # It fits
            current_chunk = proposed_text
            
    # Add remnant
    if current_chunk:
        chunks.append(current_chunk)
        
    # Optimization pass?
    # Ensure chunks are at least MIN_TOKENS if possible?
    # The prompt mainly stressed MAX size (split long sections).
    # But "Chunk size: 400-700 tokens" implies 400 is desired min.
    # Simply grouping sequentially is best effort.
    
    return chunks

def process_corpus():
    if not INPUT_FILE.exists():
        print(f"Input file {INPUT_FILE} missing.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        corpus = json.load(f)
        
    final_output = []
    
    print(f"Loaded {len(corpus)} sections. Starting chunking...")
    
    for item in corpus:
        text = item['text']
        
        # 1. Break into smallest legal units (Atoms)
        atoms = recursive_split(text)
        
        # 2. Merge into optimal chunks
        chunks_text = merge_chunks(atoms)
        
        # 3. Create objects
        # ID format: ACT-NUM-INDEX
        for idx, chunk_txt in enumerate(chunks_text, 1):
            chunk_id = f"{item['act']}-{item['number']}-{idx}"
            
            chunk_obj = {
                "id": chunk_id,
                "act": item['act'],
                "chapter": item['chapter'],
                "number": item['number'],
                "title": item['title'],
                "chunk_index": idx,
                "text": chunk_txt
            }
            final_output.append(chunk_obj)
            
    # Write
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Generated {len(final_output)} chunks.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_corpus()
