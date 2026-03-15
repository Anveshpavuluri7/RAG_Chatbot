"""
RAG engine — orchestrates retrieval and response generation.
Uses lazy initialisation for the Gemini client.
"""
from google import genai
from config import (
    LLM_MODEL,
    SIMILARITY_THRESHOLD,
)
import config
import vector_store

_client = None


def _get_client():
    global _client
    if _client is None:
        if not config.GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. "
                "Create a .env file with your key (see .env.example)."
            )
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


# ── System prompts ──────────────────────────────────────────────
_SYSTEM_PROMPT_WITH_CONTEXT = """You are a helpful AI assistant with access to the user's uploaded documents.
Use the provided document context to answer the user's question accurately.
Always cite the source document(s) in your answer.
If the context does not fully answer the question, supplement with your general knowledge but clearly indicate which parts come from the documents and which are from general knowledge.

Document Context:
{context}

Sources used: {sources}
"""

_SYSTEM_PROMPT_GENERAL = """You are a helpful AI assistant.
The user has not uploaded any relevant documents for this question, or no relevant information was found in their documents.
Answer the question using your general knowledge.
Let the user know that they can upload documents for more specific answers.
"""


def answer(question: str) -> dict:
    """
    Process a user question:
    1. Embed the query
    2. Retrieve relevant chunks from vector store
    3. Decide whether to use document context or general knowledge
    4. Generate and return the answer with sources

    Returns: {"answer": str, "sources": list[str], "used_documents": bool}
    """
    client = _get_client()

    # Step 1 – embed the query
    query_embedding = vector_store.get_embedding(question)

    # Step 2 – retrieve
    results = vector_store.query(query_embedding)

    # Step 3 – check relevance (ChromaDB cosine distance: 0 = identical)
    relevant_chunks = []
    sources = set()

    if results["ids"] and results["ids"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Convert cosine distance to similarity (1 - distance)
            similarity = 1 - distance
            if similarity >= SIMILARITY_THRESHOLD:
                relevant_chunks.append(doc)
                sources.add(meta["source"])

    # Step 4 – generate
    if relevant_chunks:
        context = "\n\n---\n\n".join(relevant_chunks)
        system_prompt = _SYSTEM_PROMPT_WITH_CONTEXT.format(
            context=context,
            sources=", ".join(sorted(sources)),
        )
        used_documents = True
    else:
        system_prompt = _SYSTEM_PROMPT_GENERAL
        used_documents = False

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=question,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,
            max_output_tokens=2048,
        ),
    )

    return {
        "answer": response.text,
        "sources": sorted(sources),
        "used_documents": used_documents,
    }
