from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import threading
import subprocess
import sys

from ai_module import get_ai_response
from verify import verify_response
from cache import get_cached, store_cached, clear_cache
from rag_retriever import retrieve_context, reload_index, get_index_version
from utils import hash_question, format_response
from scraper import scrape_url, save_text, already_scraped

load_dotenv()

app = Flask(__name__)
CORS(app)

# Absolute path to the project root (this file lives in backend/), used so
# the background index-rebuild subprocess works regardless of which
# directory `python app.py` was launched from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_INDEX_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "build_index.py")

# Track index rebuild status
_rebuild_status = {"running": False, "last": "never"}


def rebuild_index_background():
    global _rebuild_status
    _rebuild_status["running"] = True
    print("Rebuilding FAISS index...")
    try:
        subprocess.run([sys.executable, BUILD_INDEX_SCRIPT], check=True, cwd=PROJECT_ROOT)
        reload_index()  # hot-reload index in the running server
        _rebuild_status["last"] = "success"
        print("Index rebuilt successfully.")
    except Exception as e:
        _rebuild_status["last"] = f"error: {e}"
        print(f"Index rebuild failed: {e}")
    finally:
        _rebuild_status["running"] = False


# -- /ask --------------------------------------------------------------------

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    q_hash = hash_question(question)
    current_version = get_index_version()

    # Step 1: Check SQLite cache -- only reuse a cached answer if it was
    # generated against the current knowledge base. Without this check, a
    # stale answer from before a re-scrape/rebuild would be served forever.
    cached = get_cached(q_hash)
    if cached['found'] and cached.get('index_version') == current_version:
        return jsonify(format_response(cached['answer'], 'cache', cached['timestamp'], cached['sources']))

    # Step 2: Retrieve context from FAISS
    retrieved = retrieve_context(question)

    # Step 3: Call AI with context
    parsed = get_ai_response(question, retrieved['text'])

    # Step 4: Verify response
    result = verify_response(parsed)
    if not result['valid']:
        return jsonify({'error': 'Verification failed', 'details': result['errors']}), 422

    # Step 5: Store in cache, tagged with the index version used to
    # generate it, so it's correctly invalidated on the next rebuild.
    store_cached(q_hash, parsed['answer'], retrieved['sources'], current_version)

    return jsonify(format_response(parsed['answer'], 'ai', sources=retrieved['sources']))


# -- /scrape -------------------------------------------------------------------

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL -- must start with http:// or https://'}), 400

    # Check duplicate
    if already_scraped(url):
        return jsonify({'status': 'already_exists',
                        'message': 'This URL was already scraped. Index is up to date.'}), 200

    try:
        text = scrape_url(url)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 500

    if len(text) < 200:
        return jsonify({'error': 'Page has too little readable content'}), 422

    save_text(url, text)

    # Rebuild index in background so request returns immediately
    if not _rebuild_status["running"]:
        threading.Thread(target=rebuild_index_background, daemon=True).start()

    return jsonify({
        'status': 'scraped',
        'chars': len(text),
        'message': 'Content scraped. Index is rebuilding in the background.'
    })


# -- /scrape/status ------------------------------------------------------------

@app.route('/scrape/status', methods=['GET'])
def scrape_status():
    return jsonify({
        'rebuilding': _rebuild_status["running"],
        'last_result': _rebuild_status["last"]
    })


# -- /cache/clear ----------------------------------------------------------------

@app.route('/cache/clear', methods=['POST'])
def cache_clear():
    clear_cache()
    return jsonify({'status': 'cleared'})


# -- /health -------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
