# Setup File Templates

> Reference examples. Load only if unsure about file format or conventions.

## setup.sh structure

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Detect OS
case "$(uname -s)" in
  Darwin*) OS=mac ;;
  Linux*)  OS=linux ;;
  *)       OS=windows ;;
esac

# 2. Check runtime
command -v python3 >/dev/null 2>&1 || { echo "Python 3 required. Install: https://python.org"; exit 1; }

# 3. Install dependencies
pip install -r requirements.txt  # or npm install, go mod download, cargo build

# 4. Setup environment
[ -f .env ] || cp .env.example .env
echo "Edit .env and add your API keys"

# 5. Database (if needed)
python manage.py migrate  # or alembic upgrade head, prisma migrate

# 6. Verify
python -c "import app" && echo "Setup complete!" || echo "Setup failed"
echo "Run: make dev"
```

## Dockerfile (multi-stage)

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
RUN useradd -r appuser
COPY --from=builder /app /app
USER appuser
EXPOSE 8040
HEALTHCHECK CMD curl -f http://localhost:8040/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8040"]
```

## docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "${PORT:-8040}:${PORT:-8040}"
    env_file: .env
    restart: unless-stopped
  db:  # if needed
    image: postgres:16-alpine
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME:-appdb}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-localdev}
volumes:
  db_data:
```

## Makefile

```makefile
.PHONY: setup dev test build clean docker-up lint fmt help

setup:  ## First-time setup
	./setup.sh
dev:    ## Start dev server
	uvicorn app.main:app --reload --port 8040
test:   ## Run tests
	pytest
build:  ## Production build
	docker build -t app .
clean:  ## Remove artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
docker-up:  ## Start with Docker
	docker compose up --build
lint:   ## Lint
	ruff check .
fmt:    ## Format
	ruff format .
help:   ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'
.DEFAULT_GOAL := help
```

## .env.example

```bash
# Server
PORT=8040
HOST=0.0.0.0

# Database (if applicable)
DATABASE_URL=postgresql://postgres:localdev@localhost:5432/appdb

# Required — get from provider
# API_KEY=
# SECRET_KEY=

# Optional
# LOG_LEVEL=info
# DEBUG=false
```
