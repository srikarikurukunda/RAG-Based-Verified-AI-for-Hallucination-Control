import json, os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K      = 3

_model  = SentenceTransformer(MODEL_NAME)
_index  = faiss.read_index(os.getenv("FAISS_INDEX_PATH", "faiss_index/index.faiss"))
_chunks = json.load(open(os.getenv("CHUNKS_PATH", "faiss_index/chunks.json")))

def retrieve_context(question: str) -> str:
    q_vec = _model.encode([question]).astype("float32")
    _, indices = _index.search(q_vec, TOP_K)
    relevant = [_chunks[i] for i in indices[0] if i < len(_chunks)]
    return "\n\n".join(relevant)