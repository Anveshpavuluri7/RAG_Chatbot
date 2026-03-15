"""
FastAPI application — serves the chat UI and exposes upload / query / documents endpoints.
"""
import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel

import config
import document_parser
import text_chunker
import vector_store
import rag_engine

# ── App setup ───────────────────────────────────────────────────
app = FastAPI(title="RAG Chatbot", version="1.0.0")

BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


# ── Request / Response models ──────────────────────────────────
class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    used_documents: bool


# ── Routes ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document, parse it, chunk it, embed it, and store it."""
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Save to disk
    unique_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = os.path.join(config.UPLOAD_DIR, unique_name)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Parse
        raw_text = document_parser.parse(save_path)
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="The uploaded document appears to be empty.")

        # Chunk
        chunks = text_chunker.chunk_text(raw_text, file.filename)

        # Embed
        texts = [c["text"] for c in chunks]
        embeddings = vector_store.get_embeddings(texts)

        # Store
        vector_store.add_document(chunks, embeddings)

        return {
            "status": "success",
            "filename": file.filename,
            "chunks": len(chunks),
            "message": f"Successfully processed '{file.filename}' into {len(chunks)} chunks.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    """Ask a question — answered with document context or general knowledge."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = rag_engine.answer(req.question)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")


@app.get("/documents")
async def list_documents():
    """Return a list of uploaded document names."""
    docs = vector_store.list_documents()
    return {"documents": docs}


@app.delete("/documents/{doc_name}")
async def delete_document(doc_name: str):
    """Delete a specific document and its embeddings."""
    try:
        # Delete from ChromaDB
        vector_store.delete_document(doc_name)
        
        # Delete from filesystem
        deleted_files = 0
        if os.path.exists(config.UPLOAD_DIR):
            for f in os.listdir(config.UPLOAD_DIR):
                if f.endswith(f"_{doc_name}"):
                    os.remove(os.path.join(config.UPLOAD_DIR, f))
                    deleted_files += 1

        return {"status": "success", "message": f"Deleted '{doc_name}' and {deleted_files} associated files."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


@app.delete("/documents")
async def clear_all_documents():
    """Clear all documents and embeddings."""
    try:
        # Delete from ChromaDB
        vector_store.delete_collection()
        
        # Clear uploads directory
        if os.path.exists(config.UPLOAD_DIR):
            for f in os.listdir(config.UPLOAD_DIR):
                file_path = os.path.join(config.UPLOAD_DIR, f)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                
        return {"status": "success", "message": "All documents and data cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing documents: {str(e)}")
