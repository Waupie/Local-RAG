# Local-RAG

![Local RAG architecture — everything running locally](images/RAG-image.webp)

Fully local Retrieval-Augmented Generation (RAG), built with **PostgreSQL (TimescaleDB + pgai + pgvector)** for vector storage and generation, **Ollama** for local LLM inference, a **FastAPI** ingestion/retrieval service, and a simple web chat UI.

Large language models can hallucinate — producing confident but inaccurate answers when a query falls outside their training data. RAG mitigates this by retrieving relevant context from your own documents and feeding it to the model before it generates a response. The catch is that most RAG tutorials route your documents and queries through a third-party API. This project keeps everything on your machine: documents, embeddings, and generation all stay local, so nothing leaves your hardware.

## Why local RAG

- **Privacy** – documents and queries never leave your machine
- **Cost** – no per-token API bills
- **Control** – you choose the models, the database, and the retrieval logic
- **Offline-friendly** – works without an internet connection once models are pulled
- **Customization** – swap models, tune prompts, or extend the schema freely

## What's inside

- **TimescaleDB (PostgreSQL)** — vector storage via `pgvector`, with `pgai` for calling Ollama's embedding and generation models directly from SQL
- **Ollama** — hosts the local models (generation + embeddings)
- **RAG app** (FastAPI) — handles ingestion and retrieval, talks to both TimescaleDB and Ollama
- **Web chat** — vanilla HTML/JS/CSS front end for testing the bot
- **Open WebUI** *(optional)* — a fuller-featured chat UI for Ollama

## How it fits together

Everything in the diagram above runs on your machine — no document, query, or generated answer ever leaves it. Here's what each numbered step is doing:

1. **Documents** are uploaded through the web chat's Upload Files/Folders feature and sent to the RAG app for ingestion (*Data Indexing*).
2. The RAG app writes the document into the **Vector Database** — TimescaleDB, reachable at `localhost:5432` (mapped to `6434` on the host in this repo).
3. **(2a)** To index it, TimescaleDB calls out to the **Embedding Models** on Ollama (`localhost:11434`) via pgai's `ai.ollama_embed()` function, using `nomic-embed-text`. The resulting vector is stored in the same row via `pgvector`.
4. A **Query** comes in from the user and is embedded the same way, then compared against every stored vector using cosine distance (`<=>`) to find the closest matches.
5. Those **top results** are passed as context, along with the query, to the **Generation Models** on Ollama (`localhost:11434`) — `mistral:7b-instruct-q4_0` or `ministral-3:3b` — again invoked via pgai's `ai.ollama_generate()`.
6. The model's **Result** is returned to the web chat as the final answer.

Because pgai runs both the embedding and generation calls from inside PostgreSQL, the RAG app doesn't need a separate ML/embedding library glued on the side — the database and Ollama do the heavy lifting, and everything communicates over `localhost` within the Docker network.

## Requirements

- Docker Desktop (or Docker Engine)
- Docker Compose

## Quick start

1. Copy the environment file and set a secret:
   ```bash
   cp .env.example .env
   # edit .env and set INGEST_API_KEY to a strong secret
   ```
2. Build and start all services:
   ```bash
   docker compose -f docker-compose.yml up --build -d
   ```
3. Open the web chat:
   - http://localhost:8044 (RAG app)
   - http://localhost:11434 (Ollama API)

> You may want to change the ports in the docker compose file in case these are already in use on your machine.

Ollama starts in CPU mode by default, so the stack works out of the box even without an NVIDIA GPU. On first start, `init-ollama.sh` pulls the required models (`mistral:7b-instruct-q4_0`, `ministral-3:3b`, `nomic-embed-text`) into a persistent volume, so subsequent restarts skip re-downloading anything already cached.

## Services

| Service | URL | Notes |
|---|---|---|
| RAG app | http://localhost:8044 | FastAPI ingestion/retrieval API |
| Ollama | http://localhost:11434 | Local model runtime |
| TimescaleDB | `postgres://postgres:password@localhost:6434/postgres` | Vector storage (pgvector) + pgai |
| Web UI | `index.html` | Open the file directly to test the chat bot |
| Open WebUI *(optional)* | http://localhost:8080 | See below |

## Ingest documents

Drop files into the chat UI using **Upload Files/Folders**. Ingestion requests are authenticated with the `INGEST_API_KEY` you set in `.env`.

### Test with curl

You can also ingest a document directly against the RAG app's API, without the web UI:

```bash
curl -X POST http://localhost:8044/ingest \
  -H "Authorization: Bearer $INGEST_API_KEY" \
  -F "file=@/path/to/document.pdf"
```

Or send raw text/JSON instead of a file, if your endpoint supports it:

```bash
curl -X POST http://localhost:8044/ingest \
  -H "Authorization: Bearer $INGEST_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Test Document",
        "content": "This is a sample document used to verify ingestion works end to end."
      }'
```

Then query it:

```bash
curl -X POST http://localhost:8044/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is in the test document?"}'
```

> **Note:** these examples assume `POST /ingest` and `POST /query` routes with a Bearer-token `Authorization` header, matching the `INGEST_API_KEY` env var. Adjust the paths, auth header, and payload shape to match the actual routes exposed by your `rag-app` code if they differ.

## Optional: Open WebUI

Open WebUI gives you a fuller chat interface on top of the same Ollama models.

1. Start it alongside the main stack using the override file:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.openwebui.yml up --build -d
   ```
2. Open http://localhost:8080
3. Create your first admin account in the browser.
4. Pick a model available in Ollama.

If needed, pull additional models into Ollama first:
```bash
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull nomic-embed-text
```

## GPU support (NVIDIA)

If you have an NVIDIA GPU and the NVIDIA Container Toolkit installed on the host, you can enable GPU acceleration for the Ollama container with the optional override file.

1. Install NVIDIA drivers on the host.
2. Install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (host-level).
3. Restart Docker after installation.
4. Rebuild and restart with the GPU override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
   ```

Verify GPU usage:
```bash
docker logs ollama | grep -i "gpu"
```

If you don't include the GPU override file, Ollama runs in CPU mode.

## Useful commands

- View logs: `docker logs ollama`
- Stop everything: `docker compose down`

## Troubleshooting

**Shell script errors on Windows**

If you see `exec /init-ollama.sh: no such file or directory`, it's usually a Windows CRLF line-ending issue. This repo includes a `.gitattributes` rule to keep `.sh` files in LF format.

## Learn more

This project follows the same core pattern described in [Tiger Data's guide to building a local RAG app with PostgreSQL, Mistral, and Ollama](https://www.tigerdata.com/blog/build-a-fully-local-rag-app-with-postgresql-mistral-and-ollama) — PostgreSQL + pgai + pgvector for storage and model calls, Ollama for local inference — packaged here as a ready-to-run Docker Compose stack with ingestion API and web UI included.