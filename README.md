# Dastyar Agent

Lightweight RAG-based assistant focused on finding Apple products (iPhone and Apple Watch) on Digikala. This project includes scrapers to collect product data, a FAISS vector store builder, RAG retrieval and a FastAPI endpoint that exposes a chat agent powered by OpenAI models.

## Features
- Crawl Digikala for iPhone and Apple Watch product data (colors, specs, reviews).
- Persist products and reviews in a local SQL database (SQLite by default).
- Build a FAISS vector database from product text and metadata for semantic retrieval.
- RAG pipeline to answer user queries about products using the vector store and an LLM.
- An Agent with a set of Tools (filtering, summarizing reviews, comparing products, RAG search).
- FastAPI server (`/chat`) that keeps simple chat sessions and history.

## Repo layout

- `api_server.py` — FastAPI app exposing `/chat` endpoint.
- `services/` — core services:
	- `agent_creator.py` — creates LLM tools and agent.
	- `rag_service.py` — loads FAISS retriever and RAG chain.
	- `manage_sessions.py` — session and message persistence helpers.
- `scripts/` — utility scripts:
	- `data_collector.py` — fetch products, colors, specs and reviews from Digikala and store in DB.
	- `build_vector_db.py` — build FAISS vector store from DB products.
- `databases/database.py` — SQLAlchemy engine and SessionLocal factory.
- `models/model.py` — SQLAlchemy models for products, colors, sessions, and messages.
- `vectorstore/` — default location for FAISS index files.
- `Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh` — Docker configuration.

## Requirements

Python 3.12+

Dependencies are listed in `pyproject.toml` and `requirements.txt`. The main packages include:

- langchain, langchain-openai, langchain-community, OpenAI embeddings
- FAISS via `langchain_community.vectorstores.FAISS`
- FastAPI, Uvicorn
- SQLAlchemy
- requests, python-dotenv, streamlit (optional)

Install dependencies (recommended to use a virtualenv):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment

Copy `.env.example` to `.env` and set the variables:

- `DATABASE_URL` — (optional) SQLAlchemy database URL. If omitted, a local SQLite DB (`dastyar.db`) is used.
- `OPENAI_API_KEY` — required for embeddings and LLM calls.
- `MODEL` — optional LLM model name (defaults to `gpt-4o-mini` in code).

Example `.env` (already exists as `.env.example`):

```
DATABASE_URL=sqlite:///./dastyar.db
OPENAI_API_KEY=sk-...
MODEL=gpt-4o-mini
```

## Quick local workflow

1. Initialize DB tables (SQLAlchemy will auto-create tables in scripts when needed) or run:

```powershell
python -c "from databases.database import init_db; init_db()"
```

2. Collect data from Digikala (this will make HTTP requests and insert into DB):

```powershell
python scripts/data_collector.py
```

3. Build FAISS vector DB from stored products:

```powershell
python scripts/build_vector_db.py
```

4. Run the API server:

```powershell
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

5. Use the `/chat` endpoint to interact with the agent. Example request body:

```json
{
	"session_id": null,
	"message": "I want a white iPhone under 40,000,000 Toman"
}
```

The endpoint will return a `session_id` you can reuse to continue the conversation.

## Scripts and utilities

- `scripts/data_collector.py` — two stages: collect product lists and colors, then fetch detailed specs and reviews. Configure `max_pages` and delays inside the script.
- `scripts/build_vector_db.py` — builds Document objects for each product (title, price, colors, specs, reviews) and saves a FAISS index under `vectorstore/faiss_index`.

## Docker

The repo includes a `Dockerfile` and `docker-compose.yml` for containerized deployment. Review `docker-entrypoint.sh` to see how environment variables are used.

Example using docker-compose:

```powershell
docker compose up --build
```

## Notes, caveats and next steps

- The project uses OpenAI for embeddings and LLM calls — this incurs API cost.
- The scrapers target Digikala's public endpoints; respect rate limits and legal terms.
- The FAISS index uses local files — backup or store in a persistent volume for production.
- Consider adding tests, more robust error handling, and rate-limit/backoff strategies for scraping.

