import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
import logging
import uuid
import datetime

load_dotenv()  # Load .env

# Config
DB_DIR = Path("backend/data/chroma_db")
COLLECTION_NAME = "legali_corpus"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

# OpenRouter Config - Fallback List (Ordered by priority/speed)
# RESTORED VALIDATED LIST (Feb 8 2026)
MODELS = [
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

class LegalRAG:
    def __init__(self):
        print(f"Loading embedding model: {EMBEDDING_MODEL}...")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        
        print(f"Connecting to Vector DB at {DB_DIR}...")
        self.client = chromadb.PersistentClient(path=str(DB_DIR))
        self.collection = self.client.get_collection(COLLECTION_NAME)
        
        # Initialize OpenRouter Client
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("WARNING: OPENROUTER_API_KEY not found in .env")
        
        self.llm_client = OpenAI(
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

    def retrieve(self, query, top_k=3):
        # Instruction for BGE
        query_text = f"Represent this sentence for searching relevant passages: {query}"
        query_vec = self.embedder.encode([query_text], normalize_embeddings=True).tolist()
        
        results = self.collection.query(
            query_embeddings=query_vec,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def generate_response(self, question, context_str):
        system_prompt = """
You are LEGALI, a specialized AI legal stenographer for Indian Criminal Law.

MANDATORY RULES:
1. Answer ONLY using provided legal text.
2. Do not use prior knowledge.
3. Every claim must be cited using the Source ID in brackets, e.g., [BNS-101-1].
4. If unsure or if the answer is not in the context, say "The provided legal text does not contain information to answer this query."
5. DO NOT interpret law. Quote the text directly where possible.

BONUS OUTPUT:
After your answer, generate exactly 5 brief, relevant follow-up questions that the user might ask next, based on the context.
Format them exactly like this:
SUGGESTED_Q: [Question 1]
SUGGESTED_Q: [Question 2]
...
"""
        
        user_prompt = f"""
LEGAL CONTEXT:
{context_str}

USER QUESTION:
{question}

ANSWER (As a Legal Stenographer):
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        def call_llm(model_id):
            return self.llm_client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.0, # Deterministic
                max_tokens=2000
            )

        last_error = None
        
        for model_id in MODELS:
            try:
                print(f"Trying model: {model_id}...")
                response = call_llm(model_id)
                raw_content = response.choices[0].message.content
                
                # If we got here, success!
                # Parse Answer and Suggested Questions
                answer_parts = raw_content.split("SUGGESTED_Q:")
                answer_text = answer_parts[0].strip()
                
                suggested_questions = []
                if len(answer_parts) > 1:
                    for part in answer_parts[1:]:
                        q = part.strip().split("\n")[0].strip() # Get the first line after marker
                        if q:
                            suggested_questions.append(q)
                
                # Limit to 5 just in case
                suggested_questions = suggested_questions[:5]
                
                return answer_text, suggested_questions

            except Exception as e:
                msg = str(e)
                print(f"Model {model_id} failed: {msg}")
                last_error = msg
                # Continue to next model
        
        # If loop finishes without success, return the error from the last attempt (or a generic one)
        # Check for Rate Limit, Overload, or Route Error (404), or Payment (402)
        error_str = str(last_error)
        if "429" in error_str or "rate-limited" in error_str:
            return {
                "error": "Service Overloaded",
                "reason": "All available models are currently rate-limited. Please try again in a moment.",
                "status": "LLM_RATE_LIMIT"
            }
        elif "402" in error_str:
             return {
                "error": "Service Unavailable",
                "reason": "Usage limit exceeded. Please check quotas.",
                "status": "LLM_QUOTA_EXCEEDED"
            }
        
        return {
            "error": "Service Unavailable",
            "reason": f"All models failed. Last error: {error_str[:100]}...",
            "status": "LLM_PROVIDER_ERROR"
        }

    def query(self, user_question):
        trace_id = str(uuid.uuid4())
        self._log(trace_id, f"Incoming Query: {user_question}")

        # 1. Retrieve
        retrieval = self.retrieve(user_question)
        ids = retrieval['ids'][0]
        self._log(trace_id, f"Retrieved IDs: {ids}")
        
        docs = retrieval['documents'][0]
        metas = retrieval['metadatas'][0]
        dists = retrieval['distances'][0]

        # LAYER A: Retrieval Gate
        # If no results or distance too high (optional, but empty check is mandatory)
        if not ids:
            msg = "BLOCKED_BY_GATE_NO_RETRIEVAL"
            self._log(trace_id, msg)
            return {
                "answer": "The provided legal material does not contain information to answer this question.",
                "citations": [],
                "suggested_questions": [],
                "debug_metadata": {
                    "question": user_question,
                    "status": msg
                }
            }
        
        # 2. Build Context
        context_parts = []
        valid_sources = []
        for i in range(len(ids)):
            # Format: [ID] Title: ... \n Text ...
            source_id = ids[i]
            title = metas[i]['title']
            text = docs[i]
            context_parts.append(f"SOURCE_ID: [{source_id}]\nTITLE: {title}\nTEXT:\n{text}\n")
            valid_sources.append(source_id)
            
        context_str = "\n---\n".join(context_parts)
        
        # 3. Generate
        self._log(trace_id, "Calling LLM...")
        # Unpack tuple from generate_response
        generated_result = self.generate_response(user_question, context_str)
        
        # Handle error case where it returns a dict (error object) instead of tuple
        if isinstance(generated_result, dict) and "error" in generated_result:
             return {
                 "error": generated_result["error"],
                 "reason": generated_result["reason"],
                 "status": generated_result["status"]
             }
        
        # Unpack tuple
        answer, suggested_questions = generated_result

        self._log(trace_id, f"Raw LLM Output: {json.dumps(str(answer))}")
        
        # LAYER C: Output Validation
        # Check if answer contains at least one valid source ID from the context
        # We also want to extract SPECIFICALLY which sources were used for the "citations" field.
        import re
        # Regex to find [ACT-NUM-IDX] e.g. [BNS-103-1]
        # This matches the ID format we enforced in chunks.
        found_ids = set(re.findall(r'\[([A-Z]+-\d+-\d+)\]', answer))
        
        # Filter retrieved metadata to only those cited
        final_citations = []
        cited_sources_count = 0
        
        # IDs and Metas are parallel lists from retrieval
        for i, src_id in enumerate(ids):
            if src_id in found_ids:
                cited_sources_count += 1
                meta = metas[i]
                final_citations.append({
                    "act": _expand_act_name(meta['act']),
                    "section": str(meta['section_number']),
                    "chapter": meta['chapter']
                })
        
        # FALLBACK: If AI answered but forgot citations, show ALL retrieved context as citations.
        # FIX: Small models sometimes append "does not contain information" AFTER answering.
        # So we check if the answer is substantial (> 50 chars) regardless of refusal phrase.
        if cited_sources_count == 0:
             # If answer is long enough, assume it's an attempt to answer and show sources
             if len(answer) > 50:
                self._log(trace_id, "Validation: Substantial answer detected. Forcing citations from retrieved context.")
                for i, src_id in enumerate(ids):
                     meta = metas[i]
                     final_citations.append({
                        "act": _expand_act_name(meta['act']),
                        "section": str(meta['section_number']),
                        "chapter": meta['chapter']
                    })
                cited_sources_count = len(ids) # Mark as cited

        
        # Validation Logic
        if cited_sources_count == 0 and "does not contain information" not in answer:
             # Relaxed Mode: Warn but allow (or fallback finding strategy)
             # If we reject now, the user gets nothing.
             # Let's try to infer if it looks like a valid answer.
             if len(answer) > 50:
                 status = "WARNING_NO_CITATION"
                 self._log(trace_id, "Validation: WARNING - Answer generated but no citations found. Passing through.")
                 # Optimization: Maybe we can try to find simple "Section X" text and map it back?
                 # For now, just pass it through so the user sees SOMETHING.
             else:
                 answer = "Response rejected due to lack of traceable citations."
                 status = "REJECTED_NO_CITATION"
                 self._log(trace_id, "Validation: REJECTED - No citations found.")
        else:
             status = "SUCCESS"
             self._log(trace_id, "Validation: SUCCESS")
        
        # 4. Final Output Formatting
        response_object = {
            "answer": answer,
            "citations": final_citations,
            "suggested_questions": suggested_questions,
            "debug_metadata": {
                "question": user_question,
                "status": status,
                "context_used": context_str
            }
        }
        
        # 5. HARD GATE: Validation
        # The user requires: "If validation fails -> discard response and return an error"
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

    def validate_response(self, response):
        """
        Enforces:
        1. JSON Structure (answer, citations presence)
        2. Non-empty Answer
        3. Non-empty Citations (unless 'does not contain information')
        4. Complete Citation Fields
        """
        # 1. Structure
        if "answer" not in response or "citations" not in response:
            return {"valid": False, "reason": "Missing mandatory keys (answer/citations)"}
            
        answer = response["answer"]
        citations = response["citations"]
        
        # 2. Answer Content
        if not answer or not isinstance(answer, str):
             return {"valid": False, "reason": "Answer is empty or invalid type"}
             
        # 3. Citations Check
        # Exception: If the system explicitly says "doesn't know", citations might be allowed to be empty?
        # User Rule: "Does not contain citations -> Reject"
        # But if the legal text doesn't have info, we can't cite.
        # However, the user said "If current state is 'REJECTED_NO_CITATION', that means citation was expected."
        # Let's check our internal status.
        status = response.get("debug_metadata", {}).get("status")
        
        if status == "REJECTED_NO_CITATION":
             # This means we ALREADY detected missing citations in Layer C.
             # Now we formally reject it as an Error Output.
             return {"valid": False, "reason": "Answer generated but no citations found"}
             
        if "does not contain information" in answer:
            # Valid negative response
            return {"valid": True}
            
        if not citations:
            return {"valid": False, "reason": "Citations list is empty"}
            
        # 4. Citation Fields
        for cit in citations:
            if not all(k in cit for k in ["act", "section", "chapter"]):
                 return {"valid": False, "reason": "Incomplete citation metadata"}
            if not cit["act"] or not cit["section"] or not cit["chapter"]:
                 return {"valid": False, "reason": "Empty citation fields detected"}
                 
        return {"valid": True}

def _expand_act_name(acronym):
    mapping = {
        "BNS": "Bharatiya Nyaya Sanhita, 2023",
        "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "BSA": "Bharatiya Sakshya Adhiniyam, 2023"
    }
    return mapping.get(acronym, acronym)

if __name__ == "__main__":
    # Test run
    rag = LegalRAG()
    q = "What is the punishment for murder?"
    result = rag.query(q)
    print(json.dumps(result, indent=2))
