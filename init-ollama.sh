#!/bin/sh

echo "Starting Ollama server in the background..."
# Start Ollama serve in the background
ollama serve &
SERVE_PID=$!

echo "Waiting for the server to start..."
# Wait for the server to start
sleep 5

ensure_model() {
	model_name="$1"

	if ollama list | awk 'NR>1 {print $1}' | grep -qx "$model_name"; then
		echo "Model $model_name already present. Skipping pull."
	else
		echo "Pulling $model_name model..."
		ollama pull "$model_name"
	fi
}

# Pull the required models only if they are not already cached in the persistent volume.
ensure_model "mistral:7b-instruct-q4_0"
ensure_model "ministral-3:3b"
ensure_model "nomic-embed-text"

echo "All models downloaded. Ollama is ready!"
# Wait for the serve process to keep the container running
wait $SERVE_PID
