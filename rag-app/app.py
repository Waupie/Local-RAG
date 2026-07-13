from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import execute_values
import requests
import numpy as np
import os
import hmac
from typing import List, Dict

from fastapi.responses import FileResponse

from file_extraction import extract_text_from_upload

from fastapi.staticfiles import StaticFiles

from guardrails import similarity_guardrail

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Chunking utility (copied from chunk_and_ingest.py)
def chunk_code(code, chunk_size=40, overlap=10):
    lines = code.splitlines()
    chunks = []
    for i in range(0, len(lines), chunk_size - overlap):
        chunk = lines[i:i+chunk_size]
        if chunk:
            chunks.append('\n'.join(chunk))
    return chunks


app = FastAPI(title="Local RAG API")

ai_model = "ministral-3:3b"
embed_model = "nomic-embed-text"

# Allow CORS for all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "web-chat")),
    name="static",
)

# Database connection
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Ollama API functions
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
INGEST_API_KEY = os.getenv("INGEST_API_KEY", "")
GUARDRAIL_SIMILARITY_THRESHOLD = float(os.getenv("GUARDRAIL_SIMILARITY_THRESHOLD", "0.5"))

def verify_ingest_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """Require API key for ingestion endpoints so only trusted clients can add data."""
    if not INGEST_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Ingestion is disabled because INGEST_API_KEY is not configured"
        )
    if not hmac.compare_digest(x_api_key, INGEST_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def get_embedding(text: str) -> List[float]:
    """Get embedding from Ollama using nomic-embed-text"""
    response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": embed_model,
        "prompt": text,
        "keep_alive": OLLAMA_KEEP_ALIVE
    })
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        raise HTTPException(status_code=500, detail="Failed to get embedding")

def generate_response(prompt: str, context: str = "") -> str:
    """Generate response using Mistral"""
    full_prompt = f"Context: {context}\n\nQuestion: {prompt}\n\nAnswer:" if context else prompt
    response = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": ai_model,
        "prompt": full_prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE
    })
    if response.status_code == 200:
        return response.json()["response"]
    else:
        raise HTTPException(status_code=500, detail="Failed to generate response")

# Database setup
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR(768)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Pydantic models
class Document(BaseModel):
    content: str

class Query(BaseModel):
    query: str
    top_k: int = 2


def search_similar(embedding: List[float], top_k: int):
    """Find the top_k most similar chunks to the given embedding."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT content, 1 - (embedding <=> %s::vector) as similarity
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (embedding, embedding, top_k))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

# API endpoints
@app.post("/ingest")
async def ingest_document(doc: Document, _=Depends(verify_ingest_api_key)):
    """Ingest a document: chunk, generate embeddings, and store in database"""
    try:
        chunks = chunk_code(doc.content, chunk_size=40, overlap=10)
        conn = get_db_connection()
        cur = conn.cursor()
        for chunk in chunks:
            embedding = get_embedding(chunk)
            cur.execute(
                "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
                (chunk, embedding)
            )
        conn.commit()
        cur.close()
        conn.close()
        return {"message": f"Document ingested as {len(chunks)} chunk(s)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-file")
async def ingest_file(_=Depends(verify_ingest_api_key), file: UploadFile = File(...)):
    """Ingest an uploaded file (PDF or text)"""
    try:
        content = await file.read()
        text = extract_text_from_upload(file.filename, content)
        if not text:
            raise HTTPException(status_code=400, detail="No extractable text found in file")
        chunks = chunk_code(text, chunk_size=40, overlap=10)
        conn = get_db_connection()
        cur = conn.cursor()
        for chunk in chunks:
            embedding = get_embedding(chunk)
            cur.execute(
                "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
                (chunk, embedding)
            )
        conn.commit()
        cur.close()
        conn.close()
        return {"message": f"File ingested as {len(chunks)} chunk(s)"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(query: Query):
    """Query documents: guardrail against the corpus, then find similar documents and generate response"""
    try:
        allowed, best_similarity, matches = await similarity_guardrail(
            query.query,
            get_embedding_fn=get_embedding,
            search_fn=search_similar,
            top_k=query.top_k,
            threshold=GUARDRAIL_SIMILARITY_THRESHOLD,
        )

        if not allowed:
            return {
                "response": "I can only answer questions related to the documents that have been ingested.",
                "sources": [],
                "guardrail_triggered": True,
                "best_similarity": best_similarity,
            }

        # Combine context from top results
        context = "\n".join([f"Document {i+1}: {content}" for i, (content, _) in enumerate(matches)])

        # Generate response
        response = generate_response(query.query, context)

        # Return response with sources
        sources = [{"content": content, "similarity": float(similarity)} for content, similarity in matches]

        return {
            "response": response,
            "sources": sources,
            "guardrail_triggered": False,
            "best_similarity": best_similarity,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/documents")
async def list_documents():
    """List all documents (for debugging)"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, LEFT(content, 100) as preview FROM documents")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return {"documents": [{"id": r[0], "preview": r[1]} for r in results]}


@app.get("/")
async def serve_index():
    index_path = os.path.join(BASE_DIR, "web-chat", "index.html")
    return FileResponse(index_path, media_type="text/html")