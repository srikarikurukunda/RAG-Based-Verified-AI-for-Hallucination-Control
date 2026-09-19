# rag-ai-system
RAG-Based Verified AI Response System to Reduce LLM Hallucinations

## Stack
Python · Flask · FAISS · sentence-transformers · SQLite · Groq API (Llama 3.3 70B)

## How it works
1. User submits a question via the web interface
2. Flask checks the SQLite cache — if a valid cached answer exists for the current knowledge base, return it instantly
3. If not cached: generate an embedding → search FAISS → retrieve relevant context chunks (with their source URLs)
4. Build an augmented prompt (question + context) → call Groq
5. Verify the response (reasoning present, answer quality checks)
6. Store the verified answer in SQLite cache, tagged to the current knowledge base version → return to user with source citations

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment variables (.env)
```
GROQ_API_KEY=your-groq-api-key
FLASK_SECRET_KEY=any-random-word-you-make-up
FAISS_INDEX_PATH=faiss_index/index.faiss
CHUNKS_PATH=faiss_index/chunks.json
SQLITE_DB_PATH=answers.db
```

## Running
```bash
# 1. Scrape a source page (or POST to /scrape once the server is running)
python backend/scraper.py

# 2. Build the FAISS index from knowledge_base/
python scripts/build_index.py

# 3. Start the server
cd backend
python app.py
# then open frontend/index.html in a browser
```

## Testing
```bash
pip install -r requirements.txt
pytest tests/ -v
```

## API endpoints
- `POST /ask` — ask a question, returns `{answer, source, timestamp, verified, sources}`
- `POST /scrape` — scrape a URL into the knowledge base and rebuild the index in the background
- `GET /scrape/status` — poll background index-rebuild status
- `POST /cache/clear` — wipe the answer cache (useful after manually editing the knowledge base)
- `GET /health` — health check

## Future improvements
Ideas that would meaningfully extend this project, not yet implemented:

- **Relevance threshold on retrieval.** `retrieve_context` currently always returns the top 3 FAISS matches regardless of how close they actually are to the question. Checking the FAISS distance score and falling back to "not found" when nothing is close enough would reduce weakly-grounded answers.
- **Real groundedness verification.** `verify.py` currently only checks answer length, reasoning-step count, and a phrase blocklist — none of which confirm the answer is actually supported by the retrieved context. A word-overlap score between the answer and context, or a second LLM call that grades "is this answer supported by this context," would make the verification step live up to the project's name.
- **File upload ingestion.** Currently the only way to grow the knowledge base is scraping a URL. Accepting PDF/TXT uploads directly would broaden usability beyond web content.
- **Dockerfile / docker-compose.** Packaging the app (Flask + a persistent volume for `answers.db` and `faiss_index/`) would make setup a single `docker compose up` instead of manually managing a venv, `.env`, and path configuration.
- **CI via GitHub Actions.** Running `pytest tests/ -v` automatically on every push, now that the test suite actually exists.
- **Source listing/management endpoint.** A `GET /sources` endpoint to list what's currently in the knowledge base, and a way to remove a source and rebuild without it.
