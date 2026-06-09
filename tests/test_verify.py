import sys
sys.path.insert(0, 'backend')
from verify import verify_response

def test_valid_response():
    parsed = {
        'reasoning': 'Step 1: Consider X. Step 2: Apply Y.',
        'answer': 'The result is Z, because X and Y together produce Z.'
    }
    assert verify_response(parsed)['valid'] is True

def test_empty_answer_fails():
    parsed = {'reasoning': 'Step 1: ok. Step 2: ok.', 'answer': ''}
    assert verify_response(parsed)['valid'] is False

def test_missing_reasoning_fails():
    parsed = {'reasoning': '', 'answer': 'Some answer that is long enough to pass'}
    assert verify_response(parsed)['valid'] is False