import sys
from unittest.mock import MagicMock

# Mock modules that are not available in the test environment or are heavy
# We mock both 'backend.app.rag' and 'app.rag' to cover different import paths
mock_rag_module = MagicMock()
sys.modules["backend.app.rag"] = mock_rag_module
sys.modules["app.rag"] = mock_rag_module

sys.modules["chromadb"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

# Also mock backend.app.rag.LegalRAG specifically
# because the api imports it directly: from backend.app.rag import LegalRAG
mock_rag_class = MagicMock()
mock_rag_module.LegalRAG = mock_rag_class

from fastapi.testclient import TestClient
# We need to make sure we can import app.api
# If running from root, 'backend.app.api' might be the path, or just 'app.api' if PYTHONPATH is set to backend/
# The CI sets working-directory: ./backend, so PYTHONPATH usually includes ./backend, so 'app' is a top level package.
# BUT api.py adds repo root to sys.path and imports 'backend.app.rag'.

# Let's try to import app.api.
# If PYTHONPATH includes `backend`, then `import app.api` works.
try:
    from app.api import app
except ImportError:
    # Fallback if running from root without PYTHONPATH set to backend
    from backend.app.api import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "model": "LEGALI v1.0"}

def test_query_rag_success():
    # The api.py initializes `rag = LegalRAG()` at module level.
    # Since we mocked LegalRAG class before import, `rag` should be an instance of our mock.

    # We need to access the `rag` instance used by the app.
    # Accessing it via the module where it is defined.
    import app.api

    # Verify rag was initialized from our mock
    # app.api.rag is the instance
    mock_instance = app.api.rag

    # Setup return value for query method
    mock_instance.query.return_value = {
        "answer": "Test answer",
        "citations": [{"act": "BNS", "section": "1", "chapter": "1"}],
        "debug_metadata": {"status": "SUCCESS"}
    }

    response = client.post("/query", json={"query": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test answer"
    assert len(data["citations"]) == 1

def test_query_rag_logic_error():
    import app.api
    mock_instance = app.api.rag

    # Mock a logic error (e.g. validation failed)
    mock_instance.query.return_value = {
        "error": "Validation failed",
        "status": "VALIDATION_FAILED"
    }

    response = client.post("/query", json={"query": "test"})
    # The API returns 400 if "error" is in result
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "Validation failed"

def test_query_rag_exception():
    import app.api
    mock_instance = app.api.rag

    # Mock an exception
    mock_instance.query.side_effect = Exception("Catastrophic failure")

    response = client.post("/query", json={"query": "test"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Catastrophic failure"
