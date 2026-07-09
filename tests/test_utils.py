from utils import hash_question, format_response


def test_hash_question_is_deterministic():
    assert hash_question("What is RAG?") == hash_question("What is RAG?")


def test_hash_question_normalizes_case_and_whitespace():
    assert hash_question("  What Is RAG?  ") == hash_question("what is rag?")


def test_hash_question_differs_for_different_questions():
    assert hash_question("What is RAG?") != hash_question("What is FAISS?")


def test_hash_question_returns_sha256_hex():
    result = hash_question("test")
    assert len(result) == 64
    int(result, 16)  # raises ValueError if it isn't valid hex


def test_format_response_cache_source_is_verified():
    resp = format_response("answer text", "cache", "2024-01-01 00:00:00")
    assert resp == {
        "answer": "answer text",
        "source": "cache",
        "timestamp": "2024-01-01 00:00:00",
        "verified": True,
        "sources": [],
    }


def test_format_response_ai_source_is_not_verified():
    resp = format_response("answer text", "ai")
    assert resp["verified"] is False
    assert resp["timestamp"] is None


def test_format_response_includes_sources_when_given():
    resp = format_response("answer text", "ai", sources=["https://example.com"])
    assert resp["sources"] == ["https://example.com"]


def test_format_response_defaults_sources_to_empty_list():
    resp = format_response("answer text", "ai", sources=None)
    assert resp["sources"] == []
