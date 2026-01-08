import json
import re

JSON_FILE = "backend/data/structured/bnss.json"

def fix_337():
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
        
    # Find Clause 337 and 338
    c337 = next((x for x in data if x['clause_number'] == 337), None)
    c338 = next((x for x in data if x['clause_number'] == 338), None)
    
    if not c337 or not c338:
        print("Error: Could not find Clause 337 or 338")
        return

    print("Analyzing Clause 338 text...")
    text_338_raw = c338['text']
    
    # We expect the text to look like: "338. (1) ... [End of 337] ... 338. (1) ... [End of 338]"
    # We want to split at the SECOND occurrence of "338. ".
    # A robust way is to find the LAST "338. " if we assume only 2.
    # Or find "338. (1) The Public Prosecutor" unique string?
    
    # Let's search for the pattern of the Start of REAL Clause 338.
    # Title of 338 is "Appearance by Public Prosecutors."
    # Text usually starts with "338. (1) The Public Prosecutor..."
    
    split_marker = "338. (1) The Public Prosecutor"
    parts = text_338_raw.split(split_marker)
    
    if len(parts) != 2:
        # Maybe formatting is slightly different (newlines etc)?
        # Try finding just "338. (1)"
        print(f"Split marker '{split_marker}' not found cleanly. Trying alternative...")
        # Search using regex to find the second "338."
        matches = list(re.finditer(r"\s338\.\s", text_338_raw))
        
        # If the text starts with "338. ", that's match 0.
        # The second one should be the real 338.
        if len(matches) < 1:
             print("Critical: Could not find 338 markers.")
             return
             
        # If the capture included the leading "338.", match 0 is at 0.
        # But wait, looking at JSON output: "text": "338. (1) ..."
        # So it starts with 338.
        
        # Find the internal "338."
        # We can look for the pattern that looks like a new clause start.
        internal_match = re.search(r"\s+338\.\s+\(1\)", text_338_raw) # Look for " 338. (1)" in middle
        if valid_idx := (internal_match.start() if internal_match else -1):
             if valid_idx > 0:
                 part1 = text_338_raw[:valid_idx].strip()
                 part2 = text_338_raw[valid_idx:].strip()
             else:
                 print("Could not find internal split point.")
                 return
        else:
             # Try literally splitting by "338. (1)" and taking last part?
             # text_338_raw starts with "338. (1)"
             occurrences = text_338_raw.split("338. (1)")
             # ['', ' ... text of 337 ... ', ' ... text of 338 ... ']
             if len(occurrences) >= 3:
                 part1 = "338. (1)" + occurrences[1] # Reconstruct
                 part2 = "338. (1)" + occurrences[2] # Reconstruct
                 
                 # Collapse any extra chunks?
                 if len(occurrences) > 3:
                     part2 = "338. (1)" + "".join(occurrences[2:])
             else:
                 print("Could not split by '338. (1)'")
                 return
    else:
        part1 = parts[0].strip()
        part2 = split_marker + parts[1] # Add marker back
        
    print(f"Split success.")
    print(f"Part 1 (Clause 337) length: {len(part1)}")
    print(f"Part 2 (Clause 338) length: {len(part2)}")
    
    # Fix Part 1: It currently starts with "338." but should be "337."
    # Check start
    if part1.startswith("338."):
        part1 = "337." + part1[4:]
    
    # Update JSON objects
    c337['text'] = part1
    c338['text'] = part2
    
    # Remove MISSING_BODY flag if we used it (implicit by overwriting text)
    
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)
        
    print("Successfully updated bnss.json")

if __name__ == "__main__":
    fix_337()
