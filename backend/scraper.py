import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
import hashlib
import json

# This file lives in backend/, so its parent's parent is the project root.
# Anchor knowledge_base/ there instead of the process's current working
# directory (see rag_retriever.py for the full explanation).
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "knowledge_base"
OUTPUT_DIR.mkdir(exist_ok=True)
SOURCES_MAP_PATH = OUTPUT_DIR / "sources.json"


def _load_source_map() -> dict:
    if SOURCES_MAP_PATH.exists():
        try:
            return json.loads(SOURCES_MAP_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _record_source(filename: str, url: str):
    """Track which URL each scraped file came from, so build_index.py can
    attach a source citation to every chunk generated from it."""
    mapping = _load_source_map()
    mapping[filename] = url
    SOURCES_MAP_PATH.write_text(json.dumps(mapping, indent=2), encoding="utf-8")


def scrape_url(url: str) -> str:
    # Remove browser fragments like #gsc.tab=0
    url = url.split("#")[0]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
        allow_redirects=True
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove unwanted sections
    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "noscript"
    ]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def save_text(url: str, text: str):
    filename = hashlib.md5(url.encode()).hexdigest() + ".txt"
    filepath = OUTPUT_DIR / filename

    filepath.write_text(
        text,
        encoding="utf-8"
    )
    _record_source(filename, url)

    print(f"Saved: {filepath}")
    print(f"Characters: {len(text)}")


def already_scraped(url: str) -> bool:
    filename = hashlib.md5(url.encode()).hexdigest() + ".txt"
    filepath = OUTPUT_DIR / filename

    return filepath.exists()


def scrape_all(urls: list):
    for url in urls:
        try:
            text = scrape_url(url)

            if len(text) > 200:
                save_text(url, text)
                print(f"SUCCESS: {url}")
            else:
                print(f"SKIPPED (too little text): {url}")

        except Exception as e:
            print(f"FAILED: {url}")
            print(str(e))


if __name__ == "__main__":
    URLS = [
        "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
        "https://en.wikipedia.org/wiki/Large_language_model"
    ]

    scrape_all(URLS)

    print("Scraping complete.")
    print("Run: python scripts/build_index.py")
