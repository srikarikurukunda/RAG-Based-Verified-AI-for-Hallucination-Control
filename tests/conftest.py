import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make backend/ importable regardless of where pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Stub heavy / network-dependent third-party packages so importing backend
# modules never triggers a real model download, FAISS load, or a live Groq
# API call just by virtue of running the test suite. Individual tests that
# care about specific behavior monkeypatch the module-level objects they
# need (see test_rag_retriever.py, test_app.py).
if "sentence_transformers" not in sys.modules:
    st_stub = MagicMock()
    st_stub.SentenceTransformer = MagicMock(return_value=MagicMock())
    sys.modules["sentence_transformers"] = st_stub

if "faiss" not in sys.modules:
    sys.modules["faiss"] = MagicMock()

if "groq" not in sys.modules:
    groq_stub = MagicMock()
    groq_stub.Groq = MagicMock(return_value=MagicMock())
    sys.modules["groq"] = groq_stub
