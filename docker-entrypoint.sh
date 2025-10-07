#!/bin/sh
set -e

# Ensure data dir exists and is writable
mkdir -p /app/data
chown -R root:root /app/data || true

# Initialize DB (calls init_db in databases.database)
python - <<'PY'
from databases.database import init_db
try:
    init_db()
    print("✅ Database initialized")
except Exception as e:
    print("⚠️ Database init failed:", e)
PY

# Execute user CMD (uvicorn ...) or default
exec "$@"
