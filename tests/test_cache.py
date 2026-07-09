import cache


def test_get_cached_returns_not_found_for_unknown_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "answers.db"))
    result = cache.get_cached("nonexistent-hash")
    assert result == {"found": False}


def test_store_and_get_cached_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "answers.db"))

    cache.store_cached("abc123", "The answer is 42.", ["https://example.com"], "v1")
    result = cache.get_cached("abc123")

    assert result["found"] is True
    assert result["answer"] == "The answer is 42."
    assert result["sources"] == ["https://example.com"]
    assert result["index_version"] == "v1"
    assert result["timestamp"] is not None


def test_store_cached_without_sources_defaults_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "answers.db"))
    cache.store_cached("nohash", "an answer")
    result = cache.get_cached("nohash")
    assert result["sources"] == []
    assert result["index_version"] is None


def test_store_cached_upserts_instead_of_ignoring(tmp_path, monkeypatch):
    # Regression test: store_cached used to be INSERT OR IGNORE, so a
    # regenerated answer could never overwrite a stale cached row for the
    # same question hash. This is what caused stale "not found" answers to
    # survive re-scraping the knowledge base forever.
    monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "answers.db"))

    cache.store_cached("dup-hash", "first answer", ["https://old.com"], "v1")
    cache.store_cached("dup-hash", "regenerated answer", ["https://new.com"], "v2")

    result = cache.get_cached("dup-hash")
    assert result["answer"] == "regenerated answer"
    assert result["sources"] == ["https://new.com"]
    assert result["index_version"] == "v2"


def test_get_cached_creates_table_if_missing(tmp_path, monkeypatch):
    # _get_conn() runs CREATE TABLE IF NOT EXISTS -- calling get_cached on a
    # brand-new db file must not error even though no table exists yet.
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(cache, "DB_PATH", str(db_path))
    assert not db_path.exists()
    result = cache.get_cached("anything")
    assert result == {"found": False}
    assert db_path.exists()


def test_migration_preserves_rows_from_pre_sources_schema(tmp_path, monkeypatch):
    # Simulates an answers.db created before the sources/index_version
    # columns existed, to make sure upgrading doesn't lose or crash on
    # existing cached data.
    import sqlite3
    db_path = tmp_path / "old_schema.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE answers (
            question_hash TEXT PRIMARY KEY,
            answer        TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    conn.execute("INSERT INTO answers (question_hash, answer) VALUES ('oldhash', 'an old cached answer')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(cache, "DB_PATH", str(db_path))
    result = cache.get_cached("oldhash")
    assert result["found"] is True
    assert result["answer"] == "an old cached answer"
    assert result["sources"] == []
    assert result["index_version"] is None


def test_clear_cache_removes_all_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "answers.db"))
    cache.store_cached("h1", "answer one")
    cache.store_cached("h2", "answer two")
    cache.clear_cache()
    assert cache.get_cached("h1")["found"] is False
    assert cache.get_cached("h2")["found"] is False
