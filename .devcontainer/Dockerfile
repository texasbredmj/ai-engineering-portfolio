FROM mcr.microsoft.com/devcontainers/base:ubuntu24.04

# Keep the employer environment small enough for a default 32 GB Codespace.
# The application builds its own frontend and runs in separate Docker images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-venv python3-pip python-is-python3 \
    && rm -rf /var/lib/apt/lists/*
