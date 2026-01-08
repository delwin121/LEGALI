import re
import json
import sys
from pathlib import Path

INPUT_FILE = Path("backend/data/cleaned_text/bsa.txt")
OUTPUT_FILE = Path("backend/data/structured/bsa.json")

def parse_bsa():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        sys.exit(1)

    try:
        content = INPUT_FILE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Unicode dashes: Hyphen, En-dash, Em-dash
    DASH_REGEX = r"[\-\u2013\u2014]+" 
    
    # 1. Locate Body Start
    # We look for "1. Short title" - specifically the 2nd occurrence.
    # 1st is Arrangement (~350). 2nd is Body (~11560).
    matches = list(re.finditer(r"1\.\s+Short title", content))
    
    if len(matches) < 2:
        # Fallback search if arrangement is missing or structure differs
        print("Warning: Less than 2 matches for '1. Short title'. Using the last one.")
        body_start_match = matches[-1]
    else:
        body_start_match = matches[1]
        
    cursor = body_start_match.start()
    
    parsed_sections = []
    curr_n = 1
    current_chapter = "CHAPTER I PRELIMINARY"
    
    # Pre-compiled patterns
    # Section Start: "N. Title... <Dash>"
    # We use a broad dash match.
    
    while True:
        # Search for current section N at/near cursor
        pat = re.compile(rf"({curr_n})\.\s+(.*?){DASH_REGEX}")
        m = pat.search(content, cursor)
        
        if not m:
            # End of sections?
            if curr_n > 160:
                break
            else:
                # Failed prematurely
                print(f"RuntimeError: Could not find Section {curr_n} starting near {cursor}")
                sys.exit(1)
        
        # Extract title
        sec_num = int(m.group(1))
        # sec_title includes possible noise if regex matched greedily? 
        # But `.*?` is non-greedy.
        sec_title = m.group(2).strip()
        
        text_start_idx = m.end()
        
        # Look for NEXT section (N+1)
        next_n = curr_n + 1
        pat_next = re.compile(rf"\s{next_n}\.\s")
        m_next = pat_next.search(content, text_start_idx)
        
        if m_next:
            text_end_idx = m_next.start()
            next_cursor = m_next.start() + 1
        else:
            # End of file
            text_end_idx = len(content)
            next_cursor = -1
            
        raw_text_chunk = content[text_start_idx:text_end_idx]
        
        # Detect Chapter Header in the chunk (applying to next section)
        # Scan for "CHAPTER <ROMAN>"
        chap_match = re.search(r"(CHAPTER\s+[IVXLCDM]+.*)", raw_text_chunk)
        if chap_match:
             real_text = raw_text_chunk[:chap_match.start()].strip()
             new_chapter_label = raw_text_chunk[chap_match.start():].strip()
             # Cleanup spaces
             new_chapter_label = " ".join(new_chapter_label.split())
             
             parsed_sections.append({
                "chapter": current_chapter,
                "section_number": curr_n,
                "section_title": sec_title,
                "text": real_text
             })
             
             current_chapter = new_chapter_label
        else:
             parsed_sections.append({
                "chapter": current_chapter,
                "section_number": curr_n,
                "section_title": sec_title,
                "text": raw_text_chunk.strip()
             })
             
        if next_cursor == -1:
            break
        
        cursor = next_cursor
        curr_n += 1

    # Safety Check
    count = len(parsed_sections)
    if count < 160 or count > 190:
        raise RuntimeError(f"Section count sanity check failed: {count} sections found (expected 160-190).")
        
    # Write Output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(parsed_sections, f, indent=2, ensure_ascii=False)

    print(f"Total number of sections: {count}")
    print(f"output file path: {OUTPUT_FILE}")

if __name__ == "__main__":
    parse_bsa()
