import streamlit as st
import sys
from pathlib import Path

# Add backend to path so we can import app.rag
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.rag import LegalRAG

# Page Configuration
st.set_page_config(
    page_title="LEGALI - Indian Criminal Law RAG",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .main-header {
        font-size: 2.5rem;
        color: #FAFAFA;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 0 10px rgba(255,255,255,0.1);
    }
    .citation-box {
        background-color: #262730;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .source-text {
        font-family: 'Courier New', monospace;
        background-color: #1E1E1E;
        color: #E0E0E0;
        padding: 10px;
        border-radius: 5px;
        font-size: 0.9em;
        border: 1px solid #444;
    }
    /* Info box styling */
    .stAlert {
        background-color: #262730;
        color: #FAFAFA;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize RAG System (Cached)
@st.cache_resource
def get_rag_system():
    return LegalRAG()

try:
    rag = get_rag_system()
except Exception as e:
    st.error(f"Failed to initialize RAG system: {e}")
    st.stop()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/law.png", width=100)
    st.title("LEGALI")
    st.markdown("### Indian Criminal Law Assistant")
    st.info("This system answers questions based strictly on BNS, BNSS, and BSA (2023).")
    st.markdown("---")
    st.markdown("**Version:** 1.0.0 (Read-Only)")

# Main Content
st.markdown("<h1 class='main-header'>⚖️ LEGALI Research Assistant</h1>", unsafe_allow_html=True)

# Query Input
query = st.text_input("Enter your legal query here:", placeholder="e.g., What is the punishment for murder under BNS?")

if query:
    with st.spinner("Analyzing legal texts..."):
        try:
            # Get response from RAG
            response = rag.query(query)
            
            # Display Answer
            st.markdown("## 📝 Legal Opinion")
            if "error" in response:
                st.error(f"Error: {response.get('error')}")
                st.warning(f"Reason: {response.get('reason')}")
            else:
                st.success(response["answer"])
                
                # Display Citations
                if response.get("citations"):
                    st.markdown("### 📚 Citations")
                    for cit in response["citations"]:
                        st.markdown(f"- **{cit['act']}** - Section {cit['section']}, Chapter {cit['chapter']}")
                
                # Debug Metadata (Expandable)
                with st.expander("🔍 View Source Context (Debug)"):
                    debug_meta = response.get("debug_metadata", {})
                    st.markdown("#### Retrieval Status")
                    st.code(debug_meta.get("status", "UNKNOWN"))
                    
                    st.markdown("#### Context Used")
                    st.markdown(f"<div class='source-text'>{debug_meta.get('context_used', 'No context')}</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
