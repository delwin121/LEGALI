import os
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
import chromadb
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
import logging
import uuid
import datetime
import nltk
import sqlite3
import asyncio

# Download NLTK resources (quietly)
try:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except Exception as e:
    print(f"Warning: NLTK download failed: {e}")

load_dotenv()  # Load .env

# Config
DB_DIR = Path("backend/data/chroma_db")
SQLITE_DB_PATH = Path("backend/data/legali.db")
COLLECTION_NAME = "legali_corpus"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

# OpenRouter Config - Fallback List
LLM_MODEL = "google/gemini-2.5-flash" # Primary LLM Model
MODELS = [ # Fallback list, if needed
    "qwen/qwen3-coder:free",                      # User's Favorite
    "liquid/lfm-2.5-1.2b-instruct:free",          # Validated 200 OK!
    "mistralai/mistral-small-3.1-24b-instruct:free", # Validated Online
    "meta-llama/llama-3.2-3b-instruct:free",      # Standard
    "qwen/qwen-2.5-coder-32b-instruct:free",     # Backup
]
LOG_FILE = Path("backend/logs/audit.log")

# Setup Logging
logger = logging.getLogger("LEGALI")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] [TRACE_ID:%(trace_id)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

async def analyze_query_for_filters(query, client, model_id):
    prompt = f"""SYSTEM PROMPT: You are an expert Indian Criminal Law Triage Agent.
        Your goal is to bridge the lexical gap between civilian language and precise legal terminology for the Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Adhiniyam (BSA).

        RULES FOR EXPANDED QUERY:
        1. Translate civilian situational queries into specific legal charges (e.g., "car crash" -> "rash driving BNS", "fight" -> "voluntarily causing hurt BNS", "stole" -> "theft BNS", "fake document" -> "forgery BNS").
        2. Generate complete, highly descriptive sentences incorporating synonyms, legal jargon, and specific anticipated Section names or keywords.
        3. DO NOT just output a list of keywords. The expanded queries must retain the semantic intent of the original question.
        4. Generate exactly 3 distinct search variations to maximize retrieval recall.
        5. CRITICAL MAPPING: If a user asks for the definition of a "minor" in a criminal context, YOU MUST map it to "child under section 2". (e.g., "definition of a child under section 2 of BNS or POCSO").
        6. CRITICAL TRIAGE RULE: If the user describes a real-world situation or event (e.g., "my car crashed"), you MUST act as a prosecutor. Translate their story into formal criminal charges AND explicitly append the phrase "under Bharatiya Nyaya Sanhita" to Query 2 to ensure penal codes are retrieved alongside civil/motor acts.
        Example Query 2: "rash and negligent driving criminal liability under Bharatiya Nyaya Sanhita"
Analyze the user's legal query: "{query}"
Task 1: Identify if a specific Indian Act is mentioned. Options: ['BNS', 'BNSS', 'BSA', 'IT Act', 'POCSO']. If none, use "ALL".
Task 2: Generate 3 distinct search queries. 
CRITICAL RULE: In Indian Criminal Law (BNS/POCSO), the term "minor" is legally defined under the term "child" (Section 2). If the user asks for the definition of a "minor", Query 2 MUST explicitly be "definition of a child under section 2".
- Query 1: The original query cleaned up.
- Query 2: Exact legal terminology (e.g., "child").
- Query 3: Broad semantic intent.

Output ONLY a valid JSON object matching this exact format:
{{
    "act": "BNS", 
    "expanded_query": "Query 1. Query 2. Query 3."
}}
Do not output any markdown formatting like ```json."""

    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150
        )
        content = response.choices[0].message.content
        import json
        clean = content.replace("```json", "").replace("```", "").strip()
        if "{" in clean and "}" in clean:
            clean = clean[clean.find("{"):clean.rfind("}")+1]
        return json.loads(clean)
    except Exception as e:
        print(f"DEBUG: Router Failed - {e}")
        return {"act": "ALL", "expanded_query": query}

class LegalRAG:
    def __init__(self):
        print(f"Loading embedding model: {EMBEDDING_MODEL}...")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        
        print("Loading Cross-Encoder Reranker...")
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        self.reranker = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        print(f"Connecting to Vector DB at {DB_DIR}...")
        self.client = chromadb.PersistentClient(path=str(DB_DIR))
        self.collection = self.client.get_collection(COLLECTION_NAME)
        
        # Connect to SQLite
        self.conn = None
        if not SQLITE_DB_PATH.exists():
            print(f"CRITICAL WARNING: SQLITE DB NOT FOUND AT {SQLITE_DB_PATH}")
            print("Did you run migrate_to_db.py? SQLite search will be DISABLED.")
        else:
            try:
                print(f"Connecting to SQLite DB at {SQLITE_DB_PATH}...")
                self.conn = sqlite3.connect(str(SQLITE_DB_PATH), check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to connect to SQLite DB: {e}")
                self.conn = None

        # Initialize BM25 Retriever
        print("Loading documents for BM25 Sparse Retrieval...")
        from langchain_core.documents import Document
        from langchain_community.retrievers import BM25Retriever
        import json
        import os
        import uuid
        
        bm25_docs = []
        data_dir = Path("backend/data/final")
        if data_dir.exists():
            for filename in os.listdir(data_dir):
                if filename.endswith("_ready.json") or filename.endswith("_ready_v2.json"):
                    with open(data_dir / filename, 'r', encoding='utf-8') as f:
                        chunks = json.load(f)
                        for chunk in chunks:
                            meta = {
                                "act": str(chunk.get('act', '')),
                                "chapter": str(chunk.get('chapter', '')),
                                "section_number": str(chunk.get('number', '')),
                                "title": str(chunk.get('title', '')),
                                "chunk_index": int(chunk.get('chunk_index', 0)),
                                "id": str(chunk.get('id', str(uuid.uuid4())))
                            }
                            bm25_docs.append(Document(page_content=chunk.get('text', ''), metadata=meta))
                            
        if bm25_docs:
            self.bm25_retriever = BM25Retriever.from_documents(bm25_docs)
            self.bm25_retriever.k = 15
        else:
            self.bm25_retriever = None
            print("WARNING: No local documents found for BM25.")
        
        # Initialize OpenRouter Client
        api_key = os.getenv("OPENROUTER_API_KEY")
        print(f"DEBUG: API Key Found: {'Yes' if api_key else 'NO'}")
        
        if not api_key:
            print("WARNING: OPENROUTER_API_KEY not found in .env")
        
        self.sync_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or "dummy",
            default_headers={
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "LEGALI"
            }
        )
        self.async_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or "dummy",
            default_headers={
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "LEGALI"
            }
        )

    def _log(self, trace_id, message):
        extra = {'trace_id': trace_id}
        logger = logging.getLogger("LEGALI")
        logging.LoggerAdapter(logger, extra).info(message)

    def retrieve(self, query, top_k=10, fetch_k=15, lambda_mult=0.2):
        print(f"DEBUG: Starting LangChain Ensemble Retrieval for: {query}")
        
        from langchain_core.retrievers import BaseRetriever
        from langchain_core.documents import Document
        from typing import List, Any
        from langchain_core.callbacks import CallbackManagerForRetrieverRun
        from pydantic import PrivateAttr
        
        # 1. Custom Dense Retriever (Chroma)
        class CustomChromaRetriever(BaseRetriever):
            _embedder: Any = PrivateAttr()
            _collection: Any = PrivateAttr()
            k: int
            
            def __init__(self, embedder, collection, k):
                super().__init__(k=k)
                self._embedder = embedder
                self._collection = collection

            def _get_relevant_documents(self, q: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
                query_vec = self._embedder.encode([f"Represent this sentence for searching relevant passages: {q}"], normalize_embeddings=True).tolist()
                results = self._collection.query(
                    query_embeddings=query_vec, n_results=self.k,
                    include=["documents", "metadatas"]
                )
                docs = []
                if results.get('ids') and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        meta = results['metadatas'][0][i]
                        meta['id'] = results['ids'][0][i]
                        docs.append(Document(page_content=results['documents'][0][i], metadata=meta))
                return docs
                
        base_retriever = CustomChromaRetriever(embedder=self.embedder, collection=self.collection, k=fetch_k)
        
        # 2. Ensemble Fusion
        from langchain_classic.retrievers import EnsembleRetriever
        if hasattr(self, 'bm25_retriever') and self.bm25_retriever:
            ensemble_retriever = EnsembleRetriever(retrievers=[base_retriever, self.bm25_retriever], weights=[0.5, 0.5])
        else:
            ensemble_retriever = base_retriever
            
        # 3. Contextual Compression (Cross-Encoder)
        from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
        from langchain_core.documents import Document
        from langchain_core.callbacks import CallbackManagerForRetrieverRun
        from pydantic import Field
        from langchain_core.retrievers import BaseRetriever
        
        # Local definition of CrossEncoderReranker
        from langchain_core.documents.compressor import BaseDocumentCompressor
        from typing import Sequence, Any

        class CrossEncoderReranker(BaseDocumentCompressor):
            model: Any
            top_n: int = 10
            
            def compress_documents(
                self,
                documents: Sequence[Document],
                query: str,
                callbacks: Any = None,
            ) -> Sequence[Document]:
                if not documents:
                    return []
                
                pairs = [[query, doc.page_content] for doc in documents]
                scores = self.model.score(pairs)
                
                scored_docs = list(zip(documents, scores))
                scored_docs.sort(key=lambda x: x[1], reverse=True)
                
                return [doc for doc, _ in scored_docs[:self.top_n]]
        
        compressor = CrossEncoderReranker(model=self.reranker, top_n=top_k)
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=ensemble_retriever
        )
        
        # 4. Invoke Pipeline
        compressed_docs = compression_retriever.invoke(query)
        print(f"DEBUG: Successfully retrieved {len(compressed_docs)} Cross-Encoder Reranked chunks.")
        
        # 5. Map back to Stream Generator format
        final_ids = []
        final_docs = []
        final_metas = []
        final_dists = []
        
        for doc in compressed_docs:
            final_ids.append(doc.metadata.get('id', 'unknown'))
            final_docs.append(doc.page_content)
            final_metas.append(doc.metadata)
            final_dists.append(0.0)
            
        return {
            'ids': [final_ids],
            'documents': [final_docs],
            'metadatas': [final_metas],
            'distances': [final_dists]
        }

    def generate_response(self, question, context_str):
        print("DEBUG: 1. Received Query for Generation")
        
        query_lower = question.lower()
        is_comparative = any(word in query_lower for word in ["difference", "compare", "vs", "versus", "distinction", "punishment between"])
        
        if is_comparative:
            system_prompt = """You are 'Legali', an expert Legal AI. 
Your EXACT task is to compare and contrast the provided legal sections based on the user's query.
1. Read the provided context carefully.
2. Identify what Section A says.
3. Identify what Section B says.
4. Clearly explain the differences between them.
5. You MUST explicitly cite the Section numbers you are comparing.
6. Output strictly in JSON format with keys "answer" and "suggested_questions".
Do not refuse to answer; use the provided context to synthesize the comparison."""
        else:
            system_prompt = """You are 'Legali', an expert Legal AI.
1. STRICT ISOLATION: Base your answer EXCLUSIVELY on the provided context.
2. SOURCE ANCHORING: Begin every fact by stating "Under Section [X]...".
3. ZERO HALLUCINATION: Do not invent laws. If it's not in the context, say so.
4. Output strictly in JSON format with keys "answer" and "suggested_questions"."""
        
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {question}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        print("DEBUG: 2. Context Built, Messages prepared")

        def call_llm(model_id):
            return self.sync_client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.0, 
                max_tokens=1000,
                timeout=15.0 
            )

        for model_id in MODELS:
            try:
                print(f"DEBUG: 3. Sending to OpenRouter (Model: {model_id})...")
                
                response = call_llm(model_id)
                print("DEBUG: 4. Received Response from LLM")
                
                raw_content = response.choices[0].message.content
                
                try:
                    import json
                    # Remove markdown formatting if present
                    clean_content = raw_content.replace("```json", "").replace("```", "").strip()
                    
                    # Sometimes the LLM might prepend text before the JSON block.
                    # A robust approach is to slice from the first '{' to the last '}'
                    if "{" in clean_content and "}" in clean_content:
                        start_idx = clean_content.find("{")
                        end_idx = clean_content.rfind("}") + 1
                        clean_content = clean_content[start_idx:end_idx]
                        
                    parsed = json.loads(clean_content)
                    
                    # Ensure defaults if keys are missing
                    answer_text = parsed.get("answer", "No answer provided.")
                    suggestions = parsed.get("suggested_questions", [])
                    return answer_text, suggestions
                except:
                    print(f"DEBUG: JSON Parse Failed for {model_id}, returning text fallback")
                    return raw_content, ["What are the exceptions?", "Is this bailable?", "Related sections?"]

            except Exception as e:
                print(f"Model {model_id} failed: {e}")
                
        print("CRITICAL: All models failed. Returning DUMMY response.")
        return "System Error: API Connection Failed. (Showing Mock Data)", ["Check Logs", "Check API Key", "Retry Query"]

    def query(self, user_question):
        trace_id = str(uuid.uuid4())
        self._log(trace_id, f"Incoming Query: {user_question}")

        # 1. Retrieve
        print("Step 1: Retrieving documents...")
        retrieval = self.retrieve(user_question, top_k=5)
        ids = retrieval['ids'][0]
        docs = retrieval['documents'][0]
        metas = retrieval['metadatas'][0]
        
        self._log(trace_id, f"Retrieved IDs: {ids}")

        # LAYER A: Retrieval Gate
        if not ids:
            msg = "BLOCKED_BY_GATE_NO_RETRIEVAL"
            self._log(trace_id, msg)
            return {
                "answer": "The provided legal material does not contain information to answer this question.",
                "citations": [],
                "suggested_questions": [],
                "debug_metadata": {"question": user_question, "status": msg}
            }
        
        # 2. Build Context & Citations (Python Logic)
        formatted_context_parts = []
        citations = []
        seen_sections = set()
        
        for i, src_id in enumerate(ids):
            meta = metas[i] if metas[i] is not None else {}
            title = meta.get('title', 'Unknown Title')
            text = docs[i]
            
            act = _expand_act_name(meta.get('act', 'Unknown Act'))
            section = str(meta.get('section_number', meta.get('number', meta.get('section', 'Unknown Section'))))
            
            chunk_str = f"--- START {act}, SECTION {section} ---\nTITLE: {title}\nSOURCE_ID: [{src_id}]\nTEXT:\n{text}\n--- END {act}, SECTION {section} ---\n"
            formatted_context_parts.append(chunk_str)
            
            # Safely extract and sanitize the section
            raw_section = str(meta.get('number', meta.get('section_number', '')))
            if not raw_section or raw_section == "?" or "unknown" in raw_section.lower():
                display_section = "Schedule / Annexure"
            else:
                display_section = raw_section

            # Safely extract and sanitize the chapter
            raw_chapter = str(meta.get('chapter', ''))
            if not raw_chapter or "unknown" in raw_chapter.lower():
                display_chapter = "General Provisions"
            else:
                display_chapter = raw_chapter.replace("CHAPTER", "").strip()
            
            cit_key = f"{act}::{display_section}"
            
            if cit_key not in seen_sections:
                seen_sections.add(cit_key)
                citations.append({
                    "act": act,
                    "section": display_section,
                    "chapter": display_chapter,
                    "text": text[:250] + "...",
                    "id": src_id
                })
            
        context_str = "\n".join(formatted_context_parts)
        
        # 3. Generate Answer (LLM)
        self._log(trace_id, "Calling LLM...")
        print("Step 3: Calling LLM...")
        answer, suggested_questions = self.generate_response(user_question, context_str)

        self._log(trace_id, f"Raw LLM Output: {json.dumps(str(answer))}")
        
        is_refusal = "does not contain information" in answer
        if is_refusal:
             citations = []
        
        # 4. Final Output Construction
        response_object = {
            "answer": answer,
            "citations": citations,
            "suggested_questions": suggested_questions,
            "debug_metadata": {
                "question": user_question,
                "status": "SUCCESS",
                "context_used": context_str
            }
        }
        
        # 5. Validation
        validation_result = self.validate_response(response_object)
        if validation_result["valid"]:
            self._log(trace_id, f"Final Response: {json.dumps(response_object, ensure_ascii=False)}")
            return response_object
        else:
            err_obj = {
                "error": "Output Validation Failed",
                "answer": "Error: Output Validation Failed",
                "citations": [],
                "suggested_questions": [],
                "debug_metadata": {
                    "error": "Output Validation Failed",
                    "reason": validation_result["reason"],
                    "status": "VALIDATION_FAILED"
                }
            }
            self._log(trace_id, f"Final Response (ERROR): {json.dumps(err_obj)}")
            return err_obj

    async def stream_search(self, query, history=[], top_k=10, session_id=None):
        """
        Generator that yields Server-Sent Events (SSE) data.
        """
        trace_id = str(uuid.uuid4())
        self._log(trace_id, f"Incoming Stream Query: {query}")

        if session_id and self.conn:
            try:
                cursor = self.conn.cursor()
                # Check if session exists; if not, create it using the query as the title
                cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
                if not cursor.fetchone():
                    title = (query[:35] + "...") if len(query) > 35 else query
                    cursor.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (session_id, title))
                # Save user message
                cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, 'user', ?)", (session_id, query))
                self.conn.commit()
            except Exception as e:
                print(f"DEBUG: DB Save Error: {e}")

        # 0. Agentic Query Expansion (Lexical Gap Bridging)
        try:
            filters = await analyze_query_for_filters(query, self.async_client, LLM_MODEL)
            search_query = filters.get("expanded_query", query)
            self._log(trace_id, f"Expanded Search Query: {search_query}")
            print(f"DEBUG: Original Query: {query}")
            print(f"DEBUG: Expanded Search Query: {search_query}")
        except Exception as e:
            self._log(trace_id, f"Query Expansion failed: {e}")
            search_query = query
        
        # 1. Retrieve using Expanded Keywords
        retrieval = self.retrieve(search_query, top_k=top_k)
        ids = retrieval['ids'][0]
        docs = retrieval['documents'][0]
        metas = retrieval['metadatas'][0]

        # LAYER A: Retrieval Gate
        if not ids:
             msg = "The provided legal material does not contain information to answer this query."
             yield f'data: {json.dumps({"chunk": msg})}\n\n'
             await asyncio.sleep(0)
             yield f'data: {json.dumps({"citations": [], "chips": []})}\n\n'
             await asyncio.sleep(0)
             return

        # 2. Build Context & Citations
        formatted_context_parts = []
        final_citations = []
        seen_sections = set()
        
        for i, src_id in enumerate(ids):
            meta = metas[i] if metas[i] is not None else {}
            title = meta.get('title', 'Unknown Title')
            text = docs[i]
            
            act = _expand_act_name(meta.get('act', 'Unknown Act'))
            
            # Safely extract and sanitize the section
            raw_section = str(meta.get('number', meta.get('section_number', '')))
            if not raw_section or raw_section == "?" or "unknown" in raw_section.lower():
                display_section = "Schedule / Annexure"
            else:
                display_section = raw_section

            # Safely extract and sanitize the chapter
            raw_chapter = str(meta.get('chapter', ''))
            if not raw_chapter or "unknown" in raw_chapter.lower():
                display_chapter = "General Provisions"
            else:
                display_chapter = raw_chapter.replace("CHAPTER", "").strip()
            
            chunk_str = f"--- START {act}, SECTION {display_section} ---\nTITLE: {title}\nSOURCE_ID: [{src_id}]\nTEXT:\n{text}\n--- END {act}, SECTION {display_section} ---\n"
            formatted_context_parts.append(chunk_str)
            
            cit_key = f"{act}::{display_section}"
            
            if cit_key not in seen_sections:
                seen_sections.add(cit_key)
                final_citations.append({
                    "act": act,
                    "section": display_section,
                    "chapter": display_chapter,
                    "text": text[:250] + "...",
                    "id": src_id
                })
            
        context_str = "\n".join(formatted_context_parts)
        
        # 3. System Prompt
        query_lower = query.lower()
        is_comparative = any(word in query_lower for word in ["difference", "compare", "vs", "versus", "distinction", "punishment between"])
        
        if is_comparative:
            system_prompt = """You are 'Legali', an expert Legal AI. 
    Your EXACT task is to compare and contrast the provided legal sections.
    1. Read the provided context carefully.
    2. Identify what Section A says.
    3. Identify what Section B says.
    4. Clearly explain the differences between them.
    5. CITATION RULE: You MUST inject in-line citations immediately after stating any legal fact, condition, or punishment. Format the citation exactly like this: `[Section X]`. Do not wait until the end of the paragraph. Example: "The punishment for murder is death or life imprisonment [Section 103]..."
    6. Output your response in clean Markdown formatting. Do NOT output JSON. Do NOT generate suggested questions or conversational filler."""
        else:
            system_prompt = """You are 'Legali', an expert Legal AI.
    1. STRICT ISOLATION: Base your answer EXCLUSIVELY on the provided context.
    2. SOURCE ANCHORING: Begin every fact by stating "Under Section [X]...".
    3. ZERO HALLUCINATION: Do not invent laws.
    4. CITATION RULE: You MUST inject in-line citations immediately after stating any legal fact, condition, or punishment. Format the citation exactly like this: `[Section X]`. Do not wait until the end of the paragraph. Example: "...carries a maximum of ten years [Section 105]."
    5. Output your response in clean Markdown formatting. Do NOT output JSON. Do NOT generate suggested questions."""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Inject Memory
        for msg in history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
        user_prompt = f"""
LEGAL CONTEXT:
{context_str}

USER QUESTION:
{query}

ANSWER (As a Legal Stenographer):
"""
        messages.append({"role": "user", "content": user_prompt})

        # 4. Stream Generation
        full_response_text = ""
        
        try:
            model_id = LLM_MODEL
            stream = await self.async_client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.0,
                max_tokens=2000,
                stream=True,
                timeout=30.0
            )
            
            async for chunk in stream:
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content or ""
                    if content:
                        full_response_text += content
                        yield f'data: {json.dumps({"chunk": content})}\n\n'
                        await asyncio.sleep(0)
                    
        except Exception as e:
            err_msg = f"Error generating stream: {str(e)}"
            self._log(trace_id, err_msg)
            yield f'data: {json.dumps({"error": err_msg})}\n\n'
            await asyncio.sleep(0)
            return

        # 5. Post-Processing
        answer_parts = full_response_text.split("SUGGESTED_Q:")
        answer_text = answer_parts[0].strip()
        
        suggested_questions = []
        if len(answer_parts) > 1:
            for part in answer_parts[1:]:
                q = part.strip().split("\\n")[0].strip()
                if q: suggested_questions.append(q)
        suggested_questions = suggested_questions[:5]
        
        if "does not contain information" in answer_text:
             final_citations = []
        
        meta_payload = {
            "citations": final_citations,
            "chips": suggested_questions
        }
        yield f'data: {json.dumps(meta_payload)}\n\n'
        await asyncio.sleep(0)
        
        self._log(trace_id, "Stream Complete")

        if session_id and self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, 'assistant', ?)", (session_id, full_response_text))
                self.conn.commit()
            except Exception as e:
                print(f"DEBUG: DB Save Error: {e}")

    def validate_response(self, response):
        if "answer" not in response or "citations" not in response:
            return {"valid": False, "reason": "Missing mandatory keys"}
            
        answer = response["answer"]
        citations = response["citations"]
        
        if not answer or not isinstance(answer, str):
             return {"valid": False, "reason": "Answer is empty or invalid"}
             
        if "does not contain information" in answer:
            return {"valid": True}
            
        if not citations:
            return {"valid": False, "reason": "Citations list is empty"}
             
        for cit in citations:
            if not all(k in cit for k in ["act", "section", "chapter"]):
                 return {"valid": False, "reason": "Incomplete citation metadata"}

        return {"valid": True}

def _expand_act_name(acronym):
    mapping = {
        "BNS": "Bharatiya Nyaya Sanhita, 2023",
        "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "BSA": "Bharatiya Sakshya Adhiniyam, 2023",
        "Information Technology Act, 2000": "Information Technology Act, 2000"
    }
    return mapping.get(acronym, acronym)

if __name__ == "__main__":
    rag = LegalRAG()
    # q = "What is section 66A?"
    q = "What is the punishment for murder?"
    result = rag.query(q)
    print(json.dumps(result, indent=2))
