"""
Vector store module — wraps ChromaDB for storing and querying document embeddings.
Uses lazy initialisation so the app can start even without an API key.
"""
import chromadb
from google import genai
from config import (
    EMBED_MODEL,
    CHROMA_DIR,
    CHROMA_COLLECTION,
    TOP_K,
)
import config

# ── Lazy singletons ─────────────────────────────────────────────
_client = None
_chroma = None
_collection = None


def _get_genai_client():
    global _client
    if _client is None:
        if not config.GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. "
                "Create a .env file with your key (see .env.example)."
            )
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


def _get_collection():
    global _chroma, _collection
    if _collection is None:
        _chroma = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _chroma.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Embedding helpers ────────────────────────────────────────────
def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using Gemini embedding model."""
    client = _get_genai_client()
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
    )
    return [e.values for e in result.embeddings]


def get_embedding(text: str) -> list[float]:
    """Embed a single text string."""
    return get_embeddings([text])[0]


# ── ChromaDB operations ─────────────────────────────────────────
def add_document(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """
    Add document chunks + embeddings to ChromaDB.
    Each chunk dict must contain: text, chunk_id, source.
    """
    col = _get_collection()
    col.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks],
    )


def query(embedding: list[float], top_k: int = TOP_K) -> dict:
    """
    Query the vector store and return top_k results.
    Returns ChromaDB result dict with keys: ids, documents, metadatas, distances.
    """
    col = _get_collection()
    count = col.count()
    if count == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    effective_k = min(top_k, count)
    return col.query(
        query_embeddings=[embedding],
        n_results=effective_k,
    )


def list_documents() -> list[str]:
    """Return a deduplicated list of source document names in the store."""
    col = _get_collection()
    if col.count() == 0:
        return []
    all_meta = col.get(include=["metadatas"])
    sources = {m["source"] for m in all_meta["metadatas"] if m}
    return sorted(sources)


def delete_collection() -> None:
    """Delete the entire collection (useful for testing or clearing data)."""
    global _collection
    if _chroma:
        try:
            _chroma.delete_collection(CHROMA_COLLECTION)
        except ValueError:
            pass  # Collection might not exist yet
        _collection = None


def delete_document(source: str) -> None:
    """Delete all chunks belonging to a specific document source."""
    col = _get_collection()
    if col.count() > 0:
        col.delete(where={"source": source})
