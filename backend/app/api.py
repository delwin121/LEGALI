from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
from pathlib import Path
import uvicorn
import json
import time
import sqlite3

# Add backend to path
SQLITE_DB_PATH = Path("backend/data/legali.db")
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.rag import LegalRAG

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="LEGALI API",
    description="API for Indian Criminal Law RAG System",
    version="1.0.0"
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG System
# We initialize it at module level so it persists across requests
try:
    rag = LegalRAG()
except Exception as e:
    print(f"Failed to initialize RAG system: {e}")
    # We don't exit here to allow app to start, but requests will fail
    rag = None

# --- SESSION STORE ---
# In-memory dictionary: session_id -> List[messages]
sessions: Dict[str, List[Dict[str, str]]] = {}

class QueryRequest(BaseModel):
    query: str
    history: list = []

class StreamRequest(BaseModel):
    query: str
    session_id: str

class Citation(BaseModel):
    act: str
    section: str
    chapter: str
    text: Optional[str] = None
    id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    suggested_questions: List[str] = []
    debug_metadata: Dict[str, Any]

class ErrorResponse(BaseModel):
    error: str
    reason: Optional[str] = None
    status: str

@app.get("/")
def health_check():
    return {"status": "online", "model": "LEGALI v1.0"}

@app.get("/api/sessions")
def get_sessions():
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
        sessions_list = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"sessions": sessions_list}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        messages_list = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"messages": messages_list}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
def query_rag(request: QueryRequest):
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
    
    query = request.query
    history = getattr(request, 'history', []) 
    
    return StreamingResponse(
        rag.stream_search(query, history=history),
        media_type="text/event-stream"
    )

@app.post("/chat/stream")
def chat_stream(request: StreamRequest):
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
    
    session_id = request.session_id
    query = request.query
    
    print(f"Incoming Stream Request: {query} (Session: {session_id})")
    
    # 1. Get History (Now handled primarily by DB logic on frontend/rag sides, but sticking with payload history if needed)
    # The frontend is sending history in the /chat route, but not in StreamRequest.
    # The new user objective implies /chat handles history and stream_search saves it.
    history = []
    
    # 2. Generator Wrapper
    def iter_stream():
        try:
            # Call RAG Generator
            for chunk_str in rag.stream_search(query, history=history, session_id=session_id):
                yield chunk_str
        except Exception as e:
            # Yield error in SSE format
            err_json = json.dumps({"type": "error", "data": str(e)})
            yield f"data: {err_json}\\n\\n"

    return StreamingResponse(iter_stream(), media_type="text/event-stream")

# Mount frontend directory to serve static UI
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
