import os, json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

CHUNK_SIZE    = 300
CHUNK_OVERLAP = 50
MODEL_NAME    = "all-MiniLM-L6-v2"

def load_docs(folder):
    texts = []
    for f in Path(folder).glob("*.txt"):
        texts.append(f.read_text(encoding="utf-8"))
    return texts

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunks.append(" ".join(words[i:i+size]))
    return chunks

model  = SentenceTransformer(MODEL_NAME)
docs   = load_docs("knowledge_base")
chunks = [c for doc in docs for c in chunk_text(doc)]

embeddings = model.encode(chunks, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

os.makedirs("faiss_index", exist_ok=True)
faiss.write_index(index, "faiss_index/index.faiss")
with open("faiss_index/chunks.json", "w") as f:
    json.dump(chunks, f)

print(f"Done — indexed {len(chunks)} chunks.")