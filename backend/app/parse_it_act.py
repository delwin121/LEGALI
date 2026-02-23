import json
import re
from pathlib import Path
from pypdf import PdfReader

# Config
INPUT_PDF = Path("backend/data/raw_pdfs/IT-Act.pdf")
OUTPUT_JSON = Path("backend/data/final/it_act_ready.json")

def parse_it_act():
    print(f"Reading {INPUT_PDF}...")
    
    if not INPUT_PDF.exists():
        print(f"Error: {INPUT_PDF} not found.")
        return

    reader = PdfReader(INPUT_PDF)
    full_text = ""
    
    print(f"Extracting text from {len(reader.pages)} pages...")
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    # Regex to find Sections
    # Pattern: Look for "66A." or "Section 66A" type headers, but usually in bare text it might look like "\n66. Hacking..."
    # A robust pattern for Indian Acts often is: `^(\d+[A-Z]*)\.\s+(.*)` at start of lines.
    # However, PDF extraction can be messy.
    
    # Strategy: Split by "\n" and look for lines starting with number + dot.
    
    chunks = []
    lines = full_text.split('\n')
    
    current_section = None
    current_title = None
    current_text = []
    
    # Regex for Section Header: e.g. "66. Computer related offences." or "66A. Punishment for..."
    # We will assume a line starting with a number, optional letter, and a dot is a section start if it looks like a title.
    section_pattern = re.compile(r'^(\d+[A-Z]*)\.\s+(.*)')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match = section_pattern.match(line)
        if match:
            # Save previous section
            if current_section:
                chunks.append({
                    "source": "Information Technology Act, 2000",
                    "unit_type": "Section",
                    "unit_id": current_section,
                    "title": current_title,
                    "text": "\n".join(current_text).strip(),
                    "chapter": "Unknown" # extraction of chapter is harder without more structure, keeping simple
                })
            
            # Start new section
            current_section = match.group(1)
            current_title = match.group(2)
            current_text = [line]
        else:
            if current_section:
                current_text.append(line)
    
    # Save last section
    if current_section:
        chunks.append({
            "source": "Information Technology Act, 2000",
            "unit_type": "Section",
            "unit_id": current_section,
            "title": current_title,
            "text": "\n".join(current_text).strip(),
            "chapter": "Unknown"
        })
        
    print(f"Parsed {len(chunks)} sections.")
    
    # Save to JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)
        
    print(f"Saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    parse_it_act()
