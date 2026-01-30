from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import execute_values
import requests
import numpy as np
import os
from typing import List, Dict

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

# Allow CORS for all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Ollama API functions
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

def get_embedding(text: str) -> List[float]:
    """Get embedding from Ollama using nomic-embed-text"""
    response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        raise HTTPException(status_code=500, detail="Failed to get embedding")

def generate_response(prompt: str, context: str = "") -> str:
    """Generate response using Mistral"""
    full_prompt = f"Context: {context}\n\nQuestion: {prompt}\n\nAnswer:" if context else prompt
    response = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": "mistral",
        "prompt": full_prompt,
        "stream": False
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
    top_k: int = 5

# API endpoints
@app.post("/ingest")
async def ingest_document(doc: Document):
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

@app.post("/query")
async def query_documents(query: Query):
    """Query documents: find similar documents and generate response"""
    try:
        # Get query embedding
        query_embedding = get_embedding(query.query)

        # Find similar documents
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT content, 1 - (embedding <=> %s::vector) as similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, query.top_k))

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            return {"response": "No relevant documents found.", "sources": []}

        # Combine context from top results
        context = "\n".join([f"Document {i+1}: {content}" for i, (content, _) in enumerate(results)])

        # Generate response
        response = generate_response(query.query, context)

        # Return response with sources
        sources = [{"content": content, "similarity": float(similarity)} for content, similarity in results]

        return {
            "response": response,
            "sources": sources
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