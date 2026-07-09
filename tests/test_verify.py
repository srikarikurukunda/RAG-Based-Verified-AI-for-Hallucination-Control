from verify import verify_response, NOT_FOUND_PHRASE


def test_valid_response():
    parsed = {
        'reasoning': 'Step 1: Consider X. Step 2: Apply Y.',
        'answer': 'The result is Z, because X and Y together produce Z.',
    }
    assert verify_response(parsed)['valid'] is True


def test_empty_answer_fails():
    parsed = {'reasoning': 'Step 1: ok. Step 2: ok.', 'answer': ''}
    assert verify_response(parsed)['valid'] is False


def test_missing_reasoning_fails():
    parsed = {'reasoning': '', 'answer': 'Some answer that is long enough to pass'}
    assert verify_response(parsed)['valid'] is False


def test_missing_keys_do_not_crash():
    # Neither key present at all -- verify_response must not raise (this
    # used to KeyError on parsed['reasoning'] when the key was absent).
    result = verify_response({})
    assert result['valid'] is False
    assert len(result['errors']) > 0


def test_designed_not_found_message_passes():
    # ai_module.py's system prompt explicitly instructs the model to reply
    # with this exact phrase when the knowledge base doesn't have the
    # answer. It's the intended, correct response and must not be rejected
    # as an "uncertainty" failure (this was a real bug -- see verify.py).
    parsed = {
        'reasoning': 'Step 1: Searched the context. Step 2: No relevant info found.',
        'answer': 'I cannot find this in the knowledge base.',
    }
    result = verify_response(parsed)
    assert result['valid'] is True
    assert NOT_FOUND_PHRASE in parsed['answer'].lower()


def test_genuine_hedging_still_fails():
    parsed = {
        'reasoning': 'Step 1: Looked at context. Step 2: Partial match found.',
        'answer': 'I am not sure about this, it seems unclear from the context provided.',
    }
    result = verify_response(parsed)
    assert result['valid'] is False
    assert any('uncertainty phrases' in e for e in result['errors'])


def test_insufficient_reasoning_steps_fails():
    parsed = {
        'reasoning': 'Step 1: Only one step here, nothing more.',
        'answer': 'A perfectly fine and sufficiently long answer text.',
    }
    result = verify_response(parsed)
    assert result['valid'] is False
    assert any('reasoning steps' in e for e in result['errors'])
