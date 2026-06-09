from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from ai_module import get_ai_response
from verify import verify_response
from cache import get_cached, store_cached
from rag_retriever import retrieve_context
from utils import hash_question, format_response

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    q_hash = hash_question(question)

    # Step 1: Check SQLite cache
    cached = get_cached(q_hash)
    if cached['found']:
        return jsonify(format_response(cached['answer'], 'cache', cached['timestamp']))

    # Step 2: Retrieve context from FAISS
    context = retrieve_context(question)

    # Step 3: Call AI with context
    parsed = get_ai_response(question, context)

    # Step 4: Verify response
    result = verify_response(parsed)
    if not result['valid']:
        return jsonify({'error': 'Verification failed', 'details': result['errors']}), 422

    # Step 5: Store in cache
    store_cached(q_hash, parsed['answer'])

    return jsonify(format_response(parsed['answer'], 'ai'))

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)