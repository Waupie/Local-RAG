# Use the official Ollama image as base
FROM ollama/ollama:latest

# Copy the init script into the container
COPY init-ollama.sh /init-ollama.sh

# Make it executable
RUN chmod +x /init-ollama.sh

# Clear the default ENTRYPOINT
ENTRYPOINT []

# Run the init script
CMD ["/init-ollama.sh"]
