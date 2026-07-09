import os, json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

CHUNK_SIZE    = 300
CHUNK_OVERLAP = 50
MODEL_NAME    = "all-MiniLM-L6-v2"

# This file lives in scripts/, so its parent's parent is the project root.
# Anchor knowledge_base/ and faiss_index/ there instead of the process's
# current working directory, so this script produces the same result
# whether it's run directly, via `python scripts/build_index.py` from the
# project root, or spawned as a subprocess from app.py.
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
FAISS_DIR = BASE_DIR / "faiss_index"
SOURCES_MAP_PATH = KNOWLEDGE_BASE_DIR / "sources.json"


def load_source_map():
    if SOURCES_MAP_PATH.exists():
        try:
            return json.loads(SOURCES_MAP_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def load_docs(folder, source_map):
    """Returns a list of (text, source_url) pairs, one per scraped file.
    Files with no entry in sources.json (e.g. scraped before source
    tracking existed) fall back to a placeholder label instead of crashing."""
    docs = []
    for f in Path(folder).glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        source = source_map.get(f.name, "Unknown source")
        docs.append((text, source))
    return docs


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunks.append(" ".join(words[i:i+size]))
    return chunks


model = SentenceTransformer(MODEL_NAME)
source_map = load_source_map()
docs = load_docs(KNOWLEDGE_BASE_DIR, source_map)

chunks = []
for text, source in docs:
    for piece in chunk_text(text):
        chunks.append({"text": piece, "source": source})

embeddings = model.encode([c["text"] for c in chunks], show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

FAISS_DIR.mkdir(exist_ok=True)
faiss.write_index(index, str(FAISS_DIR / "index.faiss"))
with open(FAISS_DIR / "chunks.json", "w") as f:
    json.dump(chunks, f)

print(f"Done -- indexed {len(chunks)} chunks from {len(docs)} source(s).")
