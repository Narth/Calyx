FROM python:3.11-slim

# Basic dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Keep image generic; project deps installed at runtime as needed.