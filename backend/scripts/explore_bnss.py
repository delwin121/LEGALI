
def explore(filepath):
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        print(f"Total lines: {len(lines)}")
        
        # 1. Print first 20 lines to verify front matter
        print("--- HEAD ---")
        for i in range(min(20, len(lines))):
            print(f"{i+1}: {lines[i].strip()}")
            
        # 2. Find ARRANGEMENT OF CLAUSES
        print("\n--- ARRANGEMENT ---")
        for i, line in enumerate(lines[:1000]):
            if "ARRANGEMENT OF CLAUSES" in line:
                print(f"Found ARRANGEMENT at line {i+1}")
                # Print next 10 lines
                for j in range(i, i+10):
                    print(f"{j+1}: {lines[j].strip()}")
                break
                
        # 3. Find Clause 1
        print("\n--- CLAUSE 1 ---")
        for i, line in enumerate(lines[:2000]):
            # Look for exact pattern likely to be Clause 1
            if line.strip().startswith("1. Short title"):
                print(f"Found Clause 1 at line {i+1}")
                for j in range(max(0, i-5), i+10):
                    print(f"{j+1}: {lines[j].strip()}")
                break
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    explore("backend/data/cleaned_text/bnss.txt")
