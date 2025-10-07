# Dockerfile for Dastyar_agent
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr (helpful for logs)
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# system deps (keep minimal); add git if you need to install packages from git
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for better caching
COPY pyproject.toml requirements.txt ./

# Upgrade pip and install runtime requirements
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Copy rest of the project
COPY . .

# Create a directory for SQLite DB files and persisted state
RUN mkdir -p /app/data

EXPOSE 8000

# Use an entrypoint script to run DB init then start the server
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
