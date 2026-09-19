import hashlib

def hash_question(question: str) -> str:
    normalized = question.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def format_response(answer: str, source: str, timestamp=None, sources=None) -> dict:
    return {
        "answer":    answer,
        "source":    source,
        "timestamp": timestamp,
        "verified":  source == "cache",
        "sources":   sources or [],
    }
