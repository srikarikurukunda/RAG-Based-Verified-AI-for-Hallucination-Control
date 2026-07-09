import json
import os
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K      = 3

# This file lives in backend/, so its parent's parent is the project root.
# Relative paths from .env (FAISS_INDEX_PATH, CHUNKS_PATH) are written
# relative to the project root, not to whatever directory the process was
# launched from -- resolve them against BASE_DIR instead of relying on the
# current working directory, so this works no matter where `python app.py`
# is run from (and survives Flask's debug-mode auto-reloader, which
# re-launches the process with a relative script path).
BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve(path_str: str) -> str:
    p = Path(path_str)
    return str(p if p.is_absolute() else BASE_DIR / p)


FAISS_PATH  = _resolve(os.getenv("FAISS_INDEX_PATH", "faiss_index/index.faiss"))
CHUNKS_PATH = _resolve(os.getenv("CHUNKS_PATH", "faiss_index/chunks.json"))

_model  = SentenceTransformer(MODEL_NAME)
_index  = None
_chunks = []


def _load():
    global _index, _chunks
    if os.path.exists(FAISS_PATH) and os.path.exists(CHUNKS_PATH):
        _index  = faiss.read_index(FAISS_PATH)
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            _chunks = json.load(f)
        print(f"FAISS index loaded -- {len(_chunks)} chunks.")
    else:
        print("FAISS index not found. Run scripts/build_index.py first.")


def reload_index():
    """Hot-reload the index after a rebuild without restarting Flask."""
    _load()


def get_index_version() -> str:
    """A cheap fingerprint of the current index on disk, used to invalidate
    cached answers that were generated against an older knowledge base
    (see cache.py). The FAISS file's mtime changes every time
    scripts/build_index.py rewrites it, so it's a reliable-enough signal
    without needing to hash the whole index."""
    try:
        return str(os.path.getmtime(FAISS_PATH))
    except OSError:
        return "no-index"


def retrieve_context(question: str) -> dict:
    """Returns {"text": <context for the prompt>, "sources": [<url>, ...]}.

    Each chunk in chunks.json is either a plain string (older index builds,
    before source tracking existed) or {"text": ..., "source": ...}
    (current build_index.py). Both are handled so an index built before
    this feature existed doesn't crash the app -- it just won't have
    citations until it's rebuilt.
    """
    if _index is None or len(_chunks) == 0:
        return {"text": "No knowledge base available. Please scrape some URLs first.", "sources": []}

    q_vec = _model.encode([question]).astype("float32")
    _, indices = _index.search(q_vec, TOP_K)
    # FAISS returns -1 for unfilled slots when the index has fewer than
    # TOP_K vectors -- must exclude those or _chunks[-1] silently pulls in
    # the last chunk as a false match.
    matched = [_chunks[i] for i in indices[0] if 0 <= i < len(_chunks)]

    texts = [m["text"] if isinstance(m, dict) else m for m in matched]

    sources = []
    for m in matched:
        if isinstance(m, dict):
            src = m.get("source")
            if src and src not in sources:
                sources.append(src)

    return {"text": "\n\n".join(texts), "sources": sources}


# Load on import
_load()
