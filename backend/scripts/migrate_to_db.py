import sqlite3
import json
from pathlib import Path

# Config
DB_PATH = Path("backend/data/legali.db")
JSON_FILES = [
    Path("backend/data/structured/bns.json"),
    Path("backend/data/structured/bnss.json"),
    Path("backend/data/structured/bsa.json"),
    Path("backend/data/final/it_act_ready.json")
]

def migrate_to_sqlite():
    print(f"Connecting to {DB_PATH}...")
    
    # Ensure dir exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing table if any
    cursor.execute("DROP TABLE IF EXISTS legal_units")
    
    # Create FTS5 virtual table
    print("Creating FTS5 table 'legal_units'...")
    cursor.execute("""
        CREATE VIRTUAL TABLE legal_units USING fts5(
            id,
            source,
            unit_type,
            unit_id,
            text,
            chapter,
            title
        )
    """)
    
    total_records = 0
    
    for json_file in JSON_FILES:
        if not json_file.exists():
            print(f"Skipping {json_file} (Not Found)")
            continue
            
        print(f"Loading {json_file}...")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Prepare data for insertion
        rows = []
        for item in data:
            # Handle different schemas if needed
            # Common fields: unit_id, source (or filename inferred), text
            
            # For BNS/BNSS/BSA (structured folder):
            # Keys might be 'section', 'chapter', 'act', 'section_text' etc depending on previous structure.
            # Let's verify structure. Assuming user followed previous standard or we map it.
            # RAG used 'legali_ready_v2.json' which was a merged file. Here we use individual files.
            # The 'structured' files have specific keys.
            
            # Normalize fields
            # ID: unique string
            # Source: e.g. "BNS"
            # Unit Type: "Section"
            # Text: The content
            
            # Check keys
            unit_id = str(item.get("section", item.get("unit_id", "")))
            source = item.get("act", item.get("source", str(json_file.stem).upper()))
            text = item.get("text", item.get("section_text", ""))
            chapter = str(item.get("chapter", "Unknown"))
            title = item.get("title", item.get("section_title", ""))
            
            # Create a simple ID
            record_id = f"{source}_{unit_id}"
            
            rows.append((
                record_id,
                source,
                "Section", # Default
                unit_id,
                text,
                chapter,
                title
            ))
            
        cursor.executemany("INSERT INTO legal_units (id, source, unit_type, unit_id, text, chapter, title) VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        count = len(rows)
        print(f"Inserted {count} rows from {json_file.name}")
        total_records += count
        
    conn.commit()
    conn.close()
    print(f"Migration Complete. Total Records: {total_records}")

if __name__ == "__main__":
    migrate_to_sqlite()
