#!/bin/sh

echo "Starting Ollama server in the background..."
# Start Ollama serve in the background
ollama serve &
SERVE_PID=$!

echo "Waiting for the server to start..."
# Wait for the server to start
sleep 5

echo "Pulling Mistral model..."
# Pull the required models
ollama pull mistral

echo "Pulling Nomic Embed Text model..."
ollama pull nomic-embed-text

echo "All models downloaded. Ollama is ready!"
# Wait for the serve process to keep the container running
wait $SERVE_PID
