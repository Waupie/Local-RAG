import os
import requests

def warm_up_ollama():
    """Sends lightweight ping/warmup requests to Ollama so models are loaded into memory on startup."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ai_model = "mistral:7b-instruct-q4_0"
    embed_model = "nomic-embed-text"

    print("Warming up Ollama models in the background...")

    # 1. Warm up embedding model
    try:
        requests.post(
            f"{ollama_url}/api/embeddings", 
            json={
                "model": embed_model,
                "prompt": "search_query: warmup test",
                "keep_alive": OLLAMA_KEEP_ALIVE
            },
            timeout=30
        )
        print("-> Embedding model warmed up successfully!")
    except Exception as e:
        print(f"-> Warning: Embedding model warmup failed: {e}")

    # 2. Warm up LLM generation model (using num_predict=1 for instant response)
    try:
        requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ai_model,
                "prompt": "Hello",
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE,
                "options": {"num_predict": 1}
            },
            timeout=60
        )
        print("-> AI generation model warmed up successfully!")
    except Exception as e:
        print(f"-> Warning: AI model warmup failed: {e}")