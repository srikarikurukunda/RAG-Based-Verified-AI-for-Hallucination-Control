import pytest

# conftest.py stubs sentence_transformers/faiss/groq before this import, so
# importing app.py never triggers a real model load or network call.
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


# ── /ask ──────────────────────────────────────────────────────────────────

def test_ask_requires_question(client):
    res = client.post("/ask", json={"question": ""})
    assert res.status_code == 400


def test_ask_rejects_non_json_body(client):
    # Regression test: request.get_json() used to return None here and
    # crash with an unhandled AttributeError (500) instead of a clean 400.
    res = client.post("/ask", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_ask_returns_cached_answer_when_index_version_matches(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_index_version", lambda: "v1")
    monkeypatch.setattr(app_module, "get_cached", lambda h: {
        "found": True, "answer": "Cached answer.", "timestamp": "2024-01-01",
        "sources": ["https://example.com"], "index_version": "v1",
    })
    called = {"ai": False}
    monkeypatch.setattr(app_module, "get_ai_response", lambda q, c: called.update(ai=True) or {})

    res = client.post("/ask", json={"question": "What is RAG?"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["answer"] == "Cached answer."
    assert body["source"] == "cache"
    assert body["sources"] == ["https://example.com"]
    assert called["ai"] is False  # cache hit must short-circuit the AI call


def test_ask_ignores_cache_when_index_version_is_stale(client, monkeypatch):
    # Regression test for today's real bug: a cached answer generated
    # against an older knowledge base must not be served once the index
    # has been rebuilt with different content.
    monkeypatch.setattr(app_module, "get_index_version", lambda: "v2-new")
    monkeypatch.setattr(app_module, "get_cached", lambda h: {
        "found": True, "answer": "Stale answer.", "timestamp": "2024-01-01",
        "sources": [], "index_version": "v1-old",
    })
    monkeypatch.setattr(app_module, "retrieve_context", lambda q: {"text": "fresh context", "sources": ["https://new.com"]})
    monkeypatch.setattr(app_module, "get_ai_response", lambda q, c: {
        "reasoning": "Step 1: a. Step 2: b.",
        "answer": "A freshly regenerated, sufficiently long answer.",
        "raw": "raw text",
    })
    stored = {}
    monkeypatch.setattr(app_module, "store_cached", lambda h, a, s, v: stored.update(answer=a, sources=s, version=v))

    res = client.post("/ask", json={"question": "What is FAISS?"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["answer"] == "A freshly regenerated, sufficiently long answer."
    assert body["source"] == "ai"
    assert stored["version"] == "v2-new"


def test_ask_calls_ai_pipeline_on_cache_miss(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_index_version", lambda: "v1")
    monkeypatch.setattr(app_module, "get_cached", lambda h: {"found": False})
    monkeypatch.setattr(app_module, "retrieve_context", lambda q: {"text": "some context", "sources": ["https://a.com"]})
    monkeypatch.setattr(app_module, "get_ai_response", lambda q, c: {
        "reasoning": "Step 1: a. Step 2: b.",
        "answer": "A sufficiently long final answer for the test.",
        "raw": "raw text",
    })
    stored = {}
    monkeypatch.setattr(app_module, "store_cached",
                         lambda h, a, s, v: stored.update(hash=h, answer=a, sources=s, version=v))

    res = client.post("/ask", json={"question": "What is FAISS?"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["source"] == "ai"
    assert body["sources"] == ["https://a.com"]
    assert stored["answer"] == "A sufficiently long final answer for the test."


def test_ask_returns_422_when_verification_fails(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_index_version", lambda: "v1")
    monkeypatch.setattr(app_module, "get_cached", lambda h: {"found": False})
    monkeypatch.setattr(app_module, "retrieve_context", lambda q: {"text": "some context", "sources": []})
    monkeypatch.setattr(app_module, "get_ai_response", lambda q, c: {
        "reasoning": "", "answer": "", "raw": "",
    })

    res = client.post("/ask", json={"question": "What is FAISS?"})
    assert res.status_code == 422
    assert "details" in res.get_json()


def test_ask_not_found_answer_is_accepted_not_rejected(client, monkeypatch):
    # End-to-end regression check for the verify.py fix: a correct
    # "not in knowledge base" answer must reach the user, not a 422.
    monkeypatch.setattr(app_module, "get_index_version", lambda: "v1")
    monkeypatch.setattr(app_module, "get_cached", lambda h: {"found": False})
    monkeypatch.setattr(app_module, "retrieve_context", lambda q: {"text": "unrelated context", "sources": []})
    monkeypatch.setattr(app_module, "get_ai_response", lambda q, c: {
        "reasoning": "Step 1: Searched context. Step 2: No match found.",
        "answer": "I cannot find this in the knowledge base.",
        "raw": "raw text",
    })
    monkeypatch.setattr(app_module, "store_cached", lambda h, a, s, v: None)

    res = client.post("/ask", json={"question": "Unrelated question?"})
    assert res.status_code == 200
    assert res.get_json()["answer"] == "I cannot find this in the knowledge base."


# ── /scrape ───────────────────────────────────────────────────────────────

def test_scrape_requires_url(client):
    res = client.post("/scrape", json={"url": ""})
    assert res.status_code == 400


def test_scrape_rejects_non_http_url(client):
    res = client.post("/scrape", json={"url": "ftp://example.com"})
    assert res.status_code == 400


def test_scrape_returns_already_exists(client, monkeypatch):
    monkeypatch.setattr(app_module, "already_scraped", lambda u: True)
    res = client.post("/scrape", json={"url": "https://example.com"})
    assert res.status_code == 200
    assert res.get_json()["status"] == "already_exists"


def test_scrape_handles_fetch_failure(client, monkeypatch):
    monkeypatch.setattr(app_module, "already_scraped", lambda u: False)

    def _raise(u):
        raise Exception("connection refused")

    monkeypatch.setattr(app_module, "scrape_url", _raise)
    res = client.post("/scrape", json={"url": "https://example.com"})
    assert res.status_code == 500


def test_scrape_rejects_thin_content(client, monkeypatch):
    monkeypatch.setattr(app_module, "already_scraped", lambda u: False)
    monkeypatch.setattr(app_module, "scrape_url", lambda u: "too short")
    res = client.post("/scrape", json={"url": "https://example.com"})
    assert res.status_code == 422


# ── /cache/clear ─────────────────────────────────────────────────────────

def test_cache_clear_calls_clear_cache(client, monkeypatch):
    called = {"cleared": False}
    monkeypatch.setattr(app_module, "clear_cache", lambda: called.update(cleared=True))
    res = client.post("/cache/clear")
    assert res.status_code == 200
    assert res.get_json() == {"status": "cleared"}
    assert called["cleared"] is True
