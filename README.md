# Local-RAG
Fully local Retrieval-Augmented Generation (RAG) with TimescaleDB for vector storage, Ollama for local LLM inference, and a simple web chat UI.

Clone the repo and start everything with the Docker Compose command in Quick start. Ollama starts in CPU mode by default, so the stack works on machines without NVIDIA GPU support.

You may want to change the ports in the docker compose file incase these ports are occupied already.

## What’s inside
- **Ollama** (LLM runtime)
- **TimescaleDB (Postgres)** with pgvector extensions
- **RAG app** (FastAPI) for ingestion and retrieval
- **Web chat** (vanilla HTML/JS/CSS)
- **Open WebUI** (optional chat UI for Ollama)

## Requirements
- Docker Desktop (or Docker Engine)
- Docker Compose

## Quick start
1. Build and start all services:
	```bash
	docker compose -f docker-compose.yml up --build -d
	```
2. Open the web chat:
	- http://localhost:8044 (RAG app)
	- http://localhost:11434 (Ollama API)
	- http://localhost:8080 (Open WebUI)

## Services
- Ollama: http://localhost:11434
- TimescaleDB: postgres://postgres:password@localhost:6434/postgres
- RAG app: http://localhost:8044
- Open WebUI: http://localhost:8080
- Web UI to test the chat bot, open the html file (index.html)

## Open WebUI
Open WebUI is included in `docker-compose.yml` and connects to the local Ollama container.

1. Start or restart services:
	```bash
	docker compose -f docker-compose.yml up --build -d
	```
2. Open Open WebUI:
	- http://localhost:8080
3. Create your first admin account in the browser.
4. In Open WebUI, pick a model available in Ollama.

If needed, pull models into Ollama first:
```bash
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull nomic-embed-text
```

## Ingest documents
Drop files into the chat UI using **Upload Files/Folders**.

## GPU support (NVIDIA)
If you have an NVIDIA GPU and have installed the NVIDIA Container Toolkit on the host, you can enable GPU acceleration for the Ollama container with the optional override file.

1. Install NVIDIA drivers on the host.
2. Install the NVIDIA Container Toolkit (host-level):
	https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
3. Restart Docker after installation.
4. Rebuild and restart with the GPU override:
	```bash
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
	```

To verify GPU usage:
```bash
docker logs ollama | grep -i "gpu"
```

If you do not include the GPU override file, Ollama runs in CPU mode.

## Useful commands
- View logs: `docker logs ollama`
- Stop everything: `docker compose down`

## Troubleshooting
**Shell script errors on Windows**
If you see `exec /init-ollama.sh: no such file or directory`, it’s usually a Windows CRLF line-ending issue. This repo includes a `.gitattributes` rule to keep `.sh` files in LF format.
