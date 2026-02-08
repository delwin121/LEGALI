from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path
import uvicorn

# Add backend to path
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
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
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

class QueryRequest(BaseModel):
    query: str

class Citation(BaseModel):
    act: str
    section: str
    chapter: str

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

@app.post("/query", response_model=QueryResponse, responses={400: {"model": ErrorResponse}})
def query_rag(request: QueryRequest):
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
    
    try:
        result = rag.query(request.query)
        
        if "error" in result:
            # Start returning 400 for logic errors (validation failed etc)
            # Map internal status to HTTP codes
            status_code = 400
            if result.get("status") in ["LLM_RATE_LIMIT", "LLM_QUOTA_EXCEEDED", "LLM_PROVIDER_ERROR", "LLM_UNKNOWN_ERROR"]:
                status_code = 503
            elif result.get("status") == "VALIDATION_FAILED":
                status_code = 422
            
            raise HTTPException(
                status_code=status_code, 
                detail={
                    "error": result["error"],
                    "reason": result.get("reason"),
                    "status": result.get("status")
                }
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
