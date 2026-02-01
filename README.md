# Local-RAG
Fully local Retrieval-Augmented Generation (RAG) with TimescaleDB for vector storage, Ollama for local LLM inference, and a simple web chat UI.

Clone the repo and start everything with the Docker Compose command in Quick start. After installing the NVIDIA Container Toolkit, you may need to restart the Docker service or the Ollama container.

GPU support is NVIDIA-only. You can run on CPU, but it will be painfully slow slow (at least with my Ryzen 3700x).

## What’s inside
- **Ollama** (LLM runtime)
- **TimescaleDB (Postgres)** with pgvector extensions
- **RAG app** (FastAPI) for ingestion and retrieval
- **Web chat** (vanilla HTML/JS/CSS)

## Requirements
- Docker Desktop (or Docker Engine)
- Docker Compose

## Quick start
1. Build and start all services:
	```bash
	docker compose -f docker-compose.yml up --build -d
	```
2. Open the web chat:
	- http://localhost:8000 (RAG app)
	- http://localhost:11434 (Ollama API)

## Services
- Ollama: http://localhost:11434
- TimescaleDB: postgres://postgres:password@localhost:5433/postgres
- RAG app: http://localhost:8000
- Web UI to test the chat bot, open the html file (index.html)

## Ingest documents
Drop files into the chat UI using **Upload Files/Folders**.

## GPU support (NVIDIA)
This project is configured to use the NVIDIA container runtime for the Ollama container.

1. Install NVIDIA drivers on the host.
2. Install the NVIDIA Container Toolkit (host-level):
	https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
3. Restart Docker after installation.
4. Rebuild and restart:
	```bash
	docker compose build ollama
	docker compose up -d ollama
	```

To verify GPU usage:
```bash
docker logs ollama | findstr /i "gpu"
```

## Useful commands
- View logs: `docker logs ollama`
- Stop everything: `docker compose down`

## Troubleshooting
**Shell script errors on Windows**
If you see `exec /init-ollama.sh: no such file or directory`, it’s usually a Windows CRLF line-ending issue. This repo includes a `.gitattributes` rule to keep `.sh` files in LF format.
