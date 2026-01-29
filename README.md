# Local-RAG
A fully local Retrieval-Augmented Generation (RAG) system using PostgreSQL for vector storage, Ollama for local LLM inference, and Mistral models

# RAG Stack (Ollama + TimescaleDB)

## Requirements
- Docker
- Docker Compose

## Start
docker compose up -d

## Stop
docker compose down

## Services
- Ollama: http://localhost:11434
- TimescaleDB: postgres://postgres:password@localhost:5433/postgres
