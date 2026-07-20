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
from web_extraction import extract_text_from_url

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

"""
Better chunking for natural language / resumes such as PDFs, web pages, etc.
Splits on paragraphs and keeps overlap.
"""
def chunk_text(text: str, chunk_size: int = 600, overlap: int = 120) -> List[str]:
    if not text:
        return []
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para_len = len(para)
        
        if current_length + para_len > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            # Keep last paragraph for overlap
            current_chunk = current_chunk[-1:] if current_chunk else []
            current_length = len(current_chunk[0]) if current_chunk else 0
        
        current_chunk.append(para)
        current_length += para_len + 2
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


app = FastAPI(title="Local RAG API")

#ai_model = "ministral-3:3b"
ai_model = "mistral:7b-instruct-q4_0"
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
GUARDRAIL_SIMILARITY_THRESHOLD = float(os.getenv("GUARDRAIL_SIMILARITY_THRESHOLD", "0.4"))

def verify_ingest_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """Require API key for ingestion endpoints so only trusted clients can add data."""
    if not INGEST_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Ingestion is disabled because INGEST_API_KEY is not configured"
        )
    if not hmac.compare_digest(x_api_key, INGEST_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def get_embedding(text: str, is_query: bool = False) -> List[float]:
    """Get embedding from Ollama using nomic-embed-text.

    nomic-embed-text is trained with task prefixes: 'search_document: ' for
    ingested content and 'search_query: ' for queries. Without these, cosine
    similarity between genuinely matching text comes out lower/flatter than
    it should, which can trip the similarity guardrail even on relevant
    content. Documents ingested before this change must be re-ingested,
    since their stored embeddings were generated without a prefix.
    """
    prefix = "search_query: " if is_query else "search_document: "
    response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": embed_model,
        "prompt": prefix + text,
        "keep_alive": OLLAMA_KEEP_ALIVE
    })
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        raise HTTPException(status_code=500, detail="Failed to get embedding")

def generate_response(prompt: str, context: str = "") -> str:
    """Generate response using Mistral"""

    if context:
        full_prompt = f"""
            You are a precise assistant. Answer the question using ONLY the provided Context.

            Context:
            {context}

            Question: {prompt}

            Rules:
            - Base your answer only on the Context.
            - If the Context doesn't contain the information, say exactly: "I don't have that information in the provided documents."
            - Otherwise, give a clear, concise answer.
            - Do not add external knowledge.

            Answer:
        """
    else:
        full_prompt = (
            "No context was provided.\n"
            "Reply exactly: \"I don't have that information in the provided documents.\""
        )

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": ai_model,
            "prompt": full_prompt,
            "stream": False,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {
                "repeat_penalty": 1.1,
            }
        }
    )

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
async def ingest(
    _=Depends(verify_ingest_api_key),
    url: str = None,
    text: str = None,
    file: UploadFile = File(None),
):
    """Ingest a URL, raw text, or uploaded file — provide exactly one."""
    try:
        provided = sum([bool(url), bool(text), file is not None])
        if provided != 1:
            raise HTTPException(status_code=400, detail="Provide exactly one of: url, text, or file")

        if url:
            extracted = extract_text_from_url(url)
            source = url
        elif text:
            extracted = text
            source = "raw text"
        else:
            content = await file.read()
            extracted = extract_text_from_upload(file.filename, content)
            source = file.filename

        if not extracted:
            raise HTTPException(status_code=400, detail=f"No extractable text found in {source}")

        #chunks = chunk_code(extracted, chunk_size=40, overlap=10)
        chunks = chunk_text(extracted) # chunk_size: int = 600, overlap: int = 120
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
        return {"message": f"Ingested {len(chunks)} chunk(s)", "source": source}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(query: Query):
    """Query documents: guardrail against the corpus, then find similar documents and generate response"""
    try:
        allowed, best_similarity, matches = await similarity_guardrail(
            query.query,
            get_embedding_fn=lambda q: get_embedding(q, is_query=True),
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

@app.post("/debug_query")
async def debug_query(query: Query):
    try:
        embedding = get_embedding(query.query, is_query=True)
        matches = search_similar(embedding, top_k=5)
        
        return {
            "query": query.query,
            "top_similarities": [round(float(sim), 4) for _, sim in matches],
            "context_preview": [
                {
                    "similarity": round(float(sim), 4),
                    "text": content[:600] + "..." if len(content) > 600 else content
                }
                for content, sim in matches
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))