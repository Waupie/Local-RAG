# Use the official Ollama image as base
FROM ollama/ollama:latest

# Install prerequisites for NVIDIA Container Toolkit
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 && \
    rm -rf /var/lib/apt/lists/*

# Configure NVIDIA Container Toolkit repository
RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg && \
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
RUN apt-get update && \
    export NVIDIA_CONTAINER_TOOLKIT_VERSION=1.18.2-1 && \
    apt-get install -y \
        nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
        nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
        libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
        libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION} && \
    rm -rf /var/lib/apt/lists/*

# Copy the init script into the container
COPY init-ollama.sh /init-ollama.sh

# Make it executable
RUN chmod +x /init-ollama.sh

# Clear the default ENTRYPOINT
ENTRYPOINT []

# Run the init script
CMD ["/init-ollama.sh"]
