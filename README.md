# rag-ai-system
RAG-Based Verified AI Response System to Reduce LLM Hallucinations

## Stack
Python · Flask · FAISS · sentence-transformers · SQLite · Gemini/OpenAI API

## How it works
1. User submits a question via the web interface
2. Flask checks the SQLite cache — if a verified answer exists, return it instantly
3. If not cached: generate an embedding → search FAISS → retrieve relevant context chunks
4. Build an augmented prompt (question + context) → call Gemini/OpenAI
5. Verify the response (reasoning present, answer quality checks)
6. Store the verified answer in SQLite cache → return to user

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install flask sentence-transformers faiss-cpu python-dotenv requests pytest
```

## Environment variables (.env)