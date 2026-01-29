import os
import requests
import glob
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Chunk code into smaller pieces
def chunk_code(code, chunk_size=40, overlap=10):
    lines = code.splitlines()
    chunks = []
    for i in range(0, len(lines), chunk_size - overlap):
        chunk = lines[i:i+chunk_size]
        if chunk:
            chunks.append('\n'.join(chunk))
    return chunks

# Ingest a single chunk to the local server
def ingest_chunk(content, url="http://localhost:8000/ingest"):
    try:
        data = {"content": content}
        response = requests.post(url, json=data)
        if response.status_code != 200:
            return f"Failed to ingest chunk: {response.text}"
        else:
            return "Chunk ingested successfully."
    except Exception as e:
        return f"Exception during ingest: {e}"

# Process codebase files and ingest chunks concurrently
def process_codebase(root_dir, file_patterns=["**/*.py"]):
    tasks = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for pattern in file_patterns:
            for filepath in glob.glob(os.path.join(root_dir, pattern), recursive=True):
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                chunks = chunk_code(code)
                total_chunks = len(chunks)
                for idx, chunk in enumerate(chunks):
                    metadata = {  # Metadata for each chunk
                        "file": filepath,
                        "chunk": idx + 1,  # 1-based index
                        "total_chunks": total_chunks  # Total number of chunks
                    }
                    header = f"METADATA: {json.dumps(metadata)}\n"
                    tasks.append(executor.submit(ingest_chunk, header + chunk))
        for future in as_completed(tasks):
            print(future.result())

if __name__ == "__main__":
    # Change '.' to your codebase root if needed
    process_codebase(".", file_patterns=["**/*.py"])
