"""
Centralised configuration for the RAG Chatbot.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# ── Google Gemini ────────────────────────────────────────────────
def _get_api_key():
    key = os.getenv("GOOGLE_API_KEY")
    if key: return key
    # Fallback to reading .env directly if uvicorn environments are stuck
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""

def __getattr__(name):
    if name == "GOOGLE_API_KEY":
        return _get_api_key()
    raise AttributeError(f"module {__name__} has no attribute {name}")

EMBED_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-2.5-flash"

# ── Chunking ────────────────────────────────────────────────────
CHUNK_SIZE = 1000          # characters per chunk
CHUNK_OVERLAP = 200        # overlap between consecutive chunks

# ── Retrieval ───────────────────────────────────────────────────
TOP_K = 5                  # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.35  # minimum similarity to count as "relevant"

# ── ChromaDB ────────────────────────────────────────────────────
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
CHROMA_COLLECTION = "documents"

# ── Uploads ─────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
