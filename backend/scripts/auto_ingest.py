import os
import json
import uuid
import pdfplumber
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
import sys

# Ensure backend imports work
# We must add the root directory to sys.path so 'backend.app.create_chunks' can be located.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from backend.app.create_chunks import recursive_split, merge_chunks
except ImportError as e:
    print(f"Failed to import chunking engine: {e}")
    sys.exit(1)

# Config
RAW_PDF_DIR = Path("backend/data/raw_pdfs")
FINAL_DATA_DIR = Path("backend/data/final")
DB_DIR = Path("backend/data/chroma_db")
COLLECTION_NAME = "legali_corpus"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

def extract_text_from_pdf(filepath):
    print(f"Extracting text from: {filepath.name}...")
    full_text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text

def main():
    # Ensure directories exist
    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Initialize Database & Embedder
    print(f"Connecting to ChromaDB at {DB_DIR}...")
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"Loading Embedding Model ({EMBEDDING_MODEL})...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    pdfs_to_process = [f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')]
    if not pdfs_to_process:
        print("No PDF files found in backend/data/raw_pdfs/")
        return

    print(f"Found {len(pdfs_to_process)} PDFs to auto-ingest.")

    # 2. Process Loop
    for pdf_filename in pdfs_to_process:
        pdf_path = RAW_PDF_DIR / pdf_filename
        
        # Derive Act Name from filename (e.g., "NDPS Act_1985.pdf" -> "NDPS Act 1985")
        act_name_base = pdf_path.stem.replace("_", " ").title()
        
        # Define output dictionary file
        output_json_path = FINAL_DATA_DIR / f"{pdf_path.stem}_ready_v2.json"
        
        if output_json_path.exists():
            print(f"Skipping {pdf_filename}: Already processed ({output_json_path.name} exists).")
            continue
            
        print(f"\n--- Processing {act_name_base} ---")
        
        # A. Extractive Scan
        raw_text = extract_text_from_pdf(pdf_path)
        
        if not raw_text.strip():
            print(f"Warning: Extracted text from {pdf_filename} was empty!")
            continue

        # B. Hierarchical Structure Parsing 
        print("Applying Hierarchical Recursive Splitting...")
        import re
        sections = re.split(r'(?=\b(?:Section|Sec\.)\s+\d+\b)', raw_text, flags=re.IGNORECASE)
        
        structured_data = []
        global_chunk_idx = 0
        
        for sec_text in sections:
            if not sec_text.strip():
                continue
            match = re.search(r'\b(?:Section|Sec\.)\s+(\d+[A-Z]?)\b', sec_text, re.IGNORECASE)
            sec_num = match.group(1) if match else "Unknown"
            
            atomic_chunks = recursive_split(sec_text)
            merged_chunks = merge_chunks(atomic_chunks)
            
            for chunk_text in merged_chunks:
                chunk_id = f"{act_name_base.upper()}-CHUNK-{global_chunk_idx+1}"
                meta = {
                    "id": chunk_id,
                    "act": act_name_base,
                    "number": sec_num,
                    "title": f"Section {sec_num}",
                    "chapter": "Unknown",
                    "chunk_index": global_chunk_idx,
                    "text": chunk_text
                }
                structured_data.append(meta)
                global_chunk_idx += 1
                
        print(f"Generated {len(structured_data)} structural chunks.")
            
        # Write flat storage format for BM25 Engine
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=4)
        print(f"Saved structural dictionary to: {output_json_path.name}")
        
        # D. Embed and Upsert
        print("Computing dense space tensors...")
        # Text representation wrapper to mirror identical format in rag.py queries
        texts_to_encode = [f"Represent this sentence for searching relevant passages: {item['text']}" for item in structured_data]
        embeddings = embedder.encode(texts_to_encode, normalize_embeddings=True, show_progress_bar=True).tolist()
        
        ids = [item['id'] for item in structured_data]
        documents = [item['text'] for item in structured_data]
        metadatas = [{"act": item["act"], "chunk_index": item["chunk_index"], "number": str(item.get("number", "Unknown")), "title": str(item.get("title", "Unknown")), "chapter": str(item.get("chapter", "Unknown"))} for item in structured_data]
        
        batch_size = 100
        total = len(ids)
        print(f"Upserting {total} items into Vector Store...")
        
        for i in range(0, total, batch_size):
            end = min(i + batch_size, total)
            try:
                collection.upsert(
                    ids=ids[i:end],
                    embeddings=embeddings[i:end],
                    documents=documents[i:end],
                    metadatas=metadatas[i:end]
                )
            except Exception as e:
                print(f"Database batch upsert failed at indices {i}-{end}: {str(e)}")
                
        print(f"Successfully ingrained {act_name_base} into LEGALI Memory Engine.")

    print(f"\nAuto-Ingestion complete! Total DB Size: [{collection.count()}] objects.")

if __name__ == "__main__":
    main()
