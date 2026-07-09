import numpy as np

# conftest.py stubs `sentence_transformers` and `faiss` before this import,
# so this never triggers a real model download or FAISS load.
import rag_retriever as rr


class _FakeIndex:
    """Mimics faiss.Index.search() with a fixed set of neighbor ids."""

    def __init__(self, indices):
        self._indices = indices

    def search(self, q_vec, top_k):
        return np.zeros((1, len(self._indices))), np.array([self._indices])


class _FakeModel:
    def encode(self, questions):
        return np.zeros((1, 4))


def test_retrieve_context_no_index_loaded():
    rr._index = None
    rr._chunks = []
    result = rr.retrieve_context("What is RAG?")
    assert "No knowledge base available" in result["text"]
    assert result["sources"] == []


def test_retrieve_context_returns_matching_chunks_dict_format(monkeypatch):
    # Current build_index.py format: each chunk carries its source URL.
    rr._chunks = [
        {"text": "chunk A", "source": "https://a.com"},
        {"text": "chunk B", "source": "https://b.com"},
        {"text": "chunk C", "source": "https://a.com"},
    ]
    rr._index = _FakeIndex([0, 2])
    monkeypatch.setattr(rr, "_model", _FakeModel())

    result = rr.retrieve_context("question")
    assert result["text"] == "chunk A\n\nchunk C"
    assert result["sources"] == ["https://a.com"]


def test_retrieve_context_backward_compat_with_plain_string_chunks(monkeypatch):
    # An index built before source tracking existed stores plain strings,
    # not {"text", "source"} dicts. Must not crash -- just no citations.
    rr._chunks = ["chunk A", "chunk B"]
    rr._index = _FakeIndex([0, 1])
    monkeypatch.setattr(rr, "_model", _FakeModel())

    result = rr.retrieve_context("question")
    assert result["text"] == "chunk A\n\nchunk B"
    assert result["sources"] == []


def test_retrieve_context_ignores_faiss_padding_index(monkeypatch):
    # FAISS pads unfilled neighbor slots with -1 when the index has fewer
    # vectors than TOP_K. Regression test for the bug where -1 was treated
    # as a valid index and silently pulled in the last chunk.
    rr._chunks = [{"text": "only chunk", "source": "https://only.com"}]
    rr._index = _FakeIndex([0, -1, -1])
    monkeypatch.setattr(rr, "_model", _FakeModel())

    result = rr.retrieve_context("question")
    assert result["text"] == "only chunk"
    assert result["sources"] == ["https://only.com"]


def test_get_index_version_returns_string(tmp_path, monkeypatch):
    fake_path = tmp_path / "index.faiss"
    fake_path.write_text("fake")
    monkeypatch.setattr(rr, "FAISS_PATH", str(fake_path))
    version = rr.get_index_version()
    assert isinstance(version, str)
    assert version != "no-index"


def test_get_index_version_missing_file_returns_placeholder(monkeypatch):
    monkeypatch.setattr(rr, "FAISS_PATH", "/nonexistent/path/index.faiss")
    assert rr.get_index_version() == "no-index"


def test_get_index_version_changes_after_rebuild(tmp_path, monkeypatch):
    # This is the whole point of the fingerprint: a rebuilt index must
    # produce a different version so stale cache entries get invalidated.
    # Set explicit, distinct mtimes rather than relying on real-clock
    # sleep, since some filesystems only have ~1s mtime resolution.
    import os
    fake_path = tmp_path / "index.faiss"
    fake_path.write_text("v1")
    monkeypatch.setattr(rr, "FAISS_PATH", str(fake_path))
    os.utime(fake_path, (1000000000, 1000000000))
    v1 = rr.get_index_version()

    fake_path.write_text("v2 rebuilt")
    os.utime(fake_path, (1000000500, 1000000500))
    v2 = rr.get_index_version()

    assert v1 != v2
