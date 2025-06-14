# Deployment Guide

This guide explains how to run the Human Lens API locally or in production.

## Local Development

1. Install Python 3.12 and `make`.
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies and initialize the database:
   ```bash
   make dev-install
   make migrate
   ```
4. Start the server:
   ```bash
   make run
   ```
   The API will be available at [http://localhost:8000](http://localhost:8000).

## Docker

The project ships with a minimal Docker setup. To build and run with Docker Compose:

```bash
docker compose up --build
```

Environment variables are loaded from the `.env` file.

## Production

The `deploy.sh` script contains a reference deployment for Ubuntu servers without Docker. Review and adapt the script to your infrastructure.
