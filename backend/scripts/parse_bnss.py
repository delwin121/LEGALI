import re
import json
import os

INPUT_FILE = "backend/data/cleaned_text/bnss.txt"
OUTPUT_FILE = "backend/data/structured/bnss.json"

def parse_bnss():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    try:
        with open(INPUT_FILE, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Read {len(content)} characters.")

    # --- STEP 1: Parse Arrangement of Clauses ---
    # Strategy: Find text between "ARRANGEMENT OF CLAUSES" and the second "CHAPTER I" 
    # (The first "CHAPTER I" is inside the arrangement)
    
    # Actually, simpler: The Arrangement section lists chapters and clauses.
    # The real body starts after the arrangement.
    # Let's find "ARRANGEMENT OF CLAUSES"
    
    arrangement_start_match = re.search(r"ARRANGEMENT OF CLAUSES", content)
    if not arrangement_start_match:
        print("Error: Could not find ARRANGEMENT OF CLAUSES")
        return
    
    arrangement_start_idx = arrangement_start_match.end()
    
    # The body usually starts with "CHAPTER I" followed by "1. (1)"
    # Based on exploration, "1. (1)" is at index ~30983, and a "CHAPTER I" is at ~30959.
    # Let's search for "CHAPTER I" followed closely by "1. ("
    
    # We can look for the transition where the detailed "ARRANGEMENT" changes to real content.
    # However, since we saw "CHAPTER I" multiple times, let's use the index we found in exploration (~30900) as a hint,
    # or better, search for the pattern "CHAPTER I" that is followed by the TEXT of clause 1.
    
    # Let's try to extract the Arrangement Text first.
    # It ends before the start of the real Body.
    # We'll identify the Body Start by looking for "CHAPTER I" followed by "PRELIMINARY" and "1. (1)"
    
    body_start_match = re.search(r"CHAPTER I.*?PRELIMINARY.*?1\.\s*\(1\)", content, re.DOTALL)
    
    if not body_start_match:
        print("Error: Could not find start of Body (CHAPTER I ... 1. (1))")
        # Fallback to hardcoded knowledge from exploration if regex fails being too specific?
        # Exploration showed: "CHAPTER I PRELIMINARY 5 1. (1)" around index 30959
        # Let's try to find "CHAPTER I" that is NOT the one in the arrangement list.
        # The arrangement list usually says "CHAPTER I PRELIMINARY" then "1. Short title..."
        pass
    else:
        print(f"Body start match found at {body_start_match.start()}")

    # Better approach for Arrangement vs Body split:
    # The Arrangement section has "CHAPTER I" then "1. Short title..."
    # The Body section ALSO has "CHAPTER I" then "1. (1) Short title..." (Text)
    
    # Let's limit the Arrangement search zone.
    # The arrangement ends where the Body begins.
    # Let's assume Body begins at the match of "1. (1)" or "CHAPTER I" near it.
    
    matches = list(re.finditer(r"1\.\s*\(1\)", content))
    if not matches:
        print("Error: Could not find '1. (1)' start of clause 1")
        return
    
    first_clause_body_start = matches[0].start()
    print(f"Clause 1 body text starts approx at: {first_clause_body_start}")
    
    # Content before this is Front Matter + Arrangement
    pre_body_content = content[:first_clause_body_start]
    body_content = content[first_clause_body_start:]
    
    # Now parse Arrangement from pre_body_content
    # It contains lines like "CHAPTER I" and "1. Short title..."
    # Since it's a single line, they are just separated by spaces or extraction noise.
    # Regex to find "CHAPTER [Roman]" and "\d+\. [Title]"
    
    arrangement_map = {} # clause_num -> {chapter, title}
    current_chapter = "PRELIMINARY" # Default if missed
    
    # Regex for arrangement items: 
    # We iterate through the pre-body text to find sequence of Chapter ... Clauses ...
    
    # Find all potential tokens in order
    tokens = re.finditer(r"(CHAPTER\s+[IVXLCDM]+|CHAPTER\s+\d+|[A-Z\s]{5,20}\sCHAPTER)|(\d+)\.\s+([A-Z][a-zA-Z0-9\s,\(\)\-]+?)(?=\s+\d+\.|\s+CHAPTER|\s*$)", pre_body_content)
    
    # The regex above for titles is tricky because titles can vary. 
    # Let's try a simpler approach: Extract all "Number. Title" candidates.
    
    # Extract Chapters
    # Insert markers in the text to help splitting? No, read-only.
    
    # Let's just scan pre_body_content for "CHAPTER ..." and "N. Title"
    # We rely on the order.
    
    # Refined regex for Arrangement items:
    # Look for "Number. Title." which usually ends before the next Number. 
    # Titles in arrangement usually start with Capital.
    
    # Let's loop strictly.
    # Find all "CHAPTER [Roman]"
    # Find all "\d+. ..."
    
    # Helper to find all arrangement entities sorted by position
    entities = []
    
    for m in re.finditer(r"CHAPTER\s+([IVXLCDM]+)", pre_body_content):
        entities.append({"type": "chapter", "val": m.group(1), "pos": m.start()})
        
    for m in re.finditer(r"(\d+)\.\s+([^\.]+)", pre_body_content):
        # The title capture is greedy, we need to stop it before the next number or noise.
        # But in a single line file "1. Short title... 2. Definitions..." 
        # "Short title... " text might merge. 
        # We can look ahead for the next number.
        pass

    # Alternative Arrangement Parsing:
    # Split pre_body_content by "CHAPTER" and parse inside.
    # But "CHAPTER" is text.
    
    # Let's use the fact that clauses are numbering 1, 2, 3...
    # We can search for "1. ", "2. ", "3. " explicitly? No, too slow.
    
    # Iterate looking for "N. "
    curr_n = 1
    last_pos = 0
    
    # We start searching for "1. " after "Arrangement" start
    search_start = arrangement_start_idx
    
    print("Parsing Arrangement...")
    while True:
        # Find "N. " (e.g. "1. ")
        pattern = re.compile(rf"\s{curr_n}\.\s")
        match = pattern.search(pre_body_content, last_pos)
        
        if not match:
            # Maybe the number is at the start of a chunk or weirdly formatted?
            # Or we reached the end of arrangement.
            # If we reached ~531, we are good.
            if curr_n > 530:
                break
            # Try looser match?
            # print(f"Could not find clause {curr_n} in arrangement.")
            break
            
        # Found N.
        # Check if we skipped a chapter header between last_pos and match.start()
        # Look for "CHAPTER" in between
        segment = pre_body_content[last_pos:match.start()]
        chap_match = re.search(r"CHAPTER\s+([IVXLCDM]+)", segment)
        if chap_match:
            current_chapter = f"CHAPTER {chap_match.group(1)}"
            # print(f"New Chapter: {current_chapter}")
            
        start_title = match.end()
        # Title ends at the start of next number " N+1. " OR " CHAPTER" OR end of pre_body
        # We can peek for n+1
        next_n = curr_n + 1
        ensure_next = re.compile(rf"\s{next_n}\.\s|CHAPTER")
        next_match = ensure_next.search(pre_body_content, start_title)
        
        if next_match:
            end_title = next_match.start()
        else:
            end_title = len(pre_body_content)
            
        title = pre_body_content[start_title:end_title].strip()
        # Clean title: remove page numbers or trailing dots if any
        title = re.sub(r"\.*$", "", title).strip() 
        title = re.sub(r"\s+\d+$", "", title).strip() # remove potential page number suffix
        
        arrangement_map[curr_n] = {
            "chapter": current_chapter,
            "clause_title": title
        }
        
        last_pos = match.start() + 1 # Advance slightly but keep context for next search relative to this
        curr_n += 1

    print(f"Arrangement parsed: {len(arrangement_map)} clauses found.")
    
    # --- STEP 2: Parse Clause Bodies ---
    # We have body_content starting at "1. (1)..."
    # We need to extract logical chunks for "1. ...", "2. ...", etc.
    # Again, iterate 1..N
    
    parsed_clauses = []
    
    curr_n = 1
    search_start = 0 # relative to body_content
    
    # Start loop
    print("Parsing Bodies...")
    
    # Initial "1. " is at index 0 of body_content (conceptually, we matched it earlier)
    # But wait, our splitting point was `first_clause_body_start` which was the match of "1. (1)".
    # So body_content STARTS with "1. (1)..."
    # But earlier clauses (definitions) might not have (1). 
    # Wait, user prompt said: "Identify real clauses ONLY when they start like: '35. (1) ...'"
    # Does '2. Definitions' start with (1)? Usually no.
    # User said: "Parse the real clause bodies - Identify real clauses ONLY when they start like: '35. (1) ...'"
    # Maybe he implies *some* clauses start that way, or *all*?
    # Actually, BNSS "1. Short title" usually has (1). "2. Definitions" usually starts "2. (1) In this Sanhita...".
    # Inspect text for Clause 2?
    # Let's assume the pattern "N. " is the anchor.
    # And sub-sections like "(1)" are part of the body.
    
    # The prompt says: "Capture the entire clause body until the next clause number"
    # "Do NOT split sub-sections like (a), (b), (c)"
    
    # So we search for "1. ", "2. ", "3. " in sequence.
    
    while True:
        # Look for next clause start.
        # Ideally, we look for curr_n + 1.
        # If not found, look for curr_n + 2, etc. (up to 5 skipped)
        
        found_next_n = -1
        match_start = -1
        
        # Determine strict search start:
        # If previous search_start was correct, look from there.
        
        # Try to find the nearest next clause number
        # We search for range next 1 to 5
        best_match = None
        
        for lookahead in range(1, 10):
            target_n = curr_n + lookahead
            # Search pattern: " 337. "
            pattern = re.compile(rf"(\s{target_n}\.\s)")
            m = pattern.search(body_content, search_start)
            
            if m:
                # We found a future clause.
                # Is it the "best" one? 
                # We want the one with the smallest start index relative to search_start
                # But typically the file is ordered. So if we find N+1, that's it.
                # If we find N+2 but NOT N+1 within a reasonable distance, N+1 is missing.
                # But "search" finds the *first* occurrence.
                
                # Check if this match is "too far"? No, simple lookahead.
                # We essentially accept the first match of ANY (N+1..N+5)
                # But wait, if text references "Section 500" later, we might false match.
                # But we are dealing with N=337.
                
                # Optimization: find ALL matches for N+1..N+5 in next chunk?
                # No, just iterate order.
                
                if best_match is None or m.start() < best_match.start():
                    best_match = m
                    found_next_n = target_n
                    
                # If we found N+1 immediately, break optimization?
                if lookahead == 1:
                     break
        
        if not best_match:
             # Check for end of file / last clause
             if curr_n >= 531:
                 # Assume end
                 text_chunk = body_content[search_start:].strip()
                 parsed_clauses.append({
                     "clause_number": curr_n,
                     "text": text_chunk
                 })
                 break
             else:
                 print(f"Stopping body parse at {curr_n}. No subsequent clauses found.")
                 break
                 
        # We found a next clause (found_next_n) at best_match
        # The text for curr_n is from search_start to best_match.start()
        
        text_chunk = body_content[search_start:best_match.start()].strip()
        
        parsed_clauses.append({
            "clause_number": curr_n,
            "text": text_chunk
        })
        
        # If we skipped clauses (e.g. found N+2 instead of N+1)
        # We should ideally record N+1 as missing.
        if found_next_n > curr_n + 1:
            for missing_n in range(curr_n + 1, found_next_n):
                print(f"Warning: Clause {missing_n} body missing/skipped.")
                parsed_clauses.append({
                    "clause_number": missing_n,
                    "text": "MISSING_BODY" 
                })
        
        curr_n = found_next_n
        search_start = best_match.start() + 1

    # --- STEP 3: Merge ---
    print(f"Extracted {len(parsed_clauses)} clause bodies.")
    
    final_output = []
    
    for item in parsed_clauses:
        num = item['clause_number']
        arr_info = arrangement_map.get(num, {})
        
        # Fallback if title missing? 
        title = arr_info.get("clause_title", "")
        chapter = arr_info.get("chapter", "")
        
        # Clean text
        # Remove the "N. " from the start of text? 
        # User wants "text": string. Usually includes the content. 
        # "Capture the entire clause body"
        # We can clean the leading "N. " if desired, but retaining it is safe.
        
        obj = {
            "chapter": chapter,
            "clause_number": num,
            "clause_title": title,
            "text": item['text']
        }
        
        # Validation checks
        if not title:
            # print(f"Warning: No title for Clause {num}")
            pass # Report or accept? User: "If a clause title exists... error"?
            # Prompt: "If a clause body exists but title is missing -> error"
            # We should probably flag it.
        
        final_output.append(obj)
        
    # Write JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(final_output, f, indent=2)
        
    print(f"Successfully wrote {len(final_output)} clauses to {OUTPUT_FILE}")

if __name__ == "__main__":
    parse_bnss()
