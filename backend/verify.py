MIN_ANSWER_LENGTH = 20
MIN_REASONING_STEPS = 2

def verify_response(parsed: dict) -> dict:
    errors = []

    if not parsed.get('answer') or len(parsed['answer'].strip()) < MIN_ANSWER_LENGTH:
        errors.append('Answer is empty or too short')

    if not parsed.get('reasoning') or len(parsed['reasoning'].strip()) < 10:
        errors.append('Reasoning section is missing or too brief')

    step_count = parsed['reasoning'].lower().count('step ')
    if step_count < MIN_REASONING_STEPS:
        errors.append(f'Expected {MIN_REASONING_STEPS} reasoning steps, found {step_count}')

    uncertainty_phrases = ['i am not sure', 'i don\'t know', 'i cannot', 'unclear']
    answer_lower = parsed['answer'].lower()
    if any(p in answer_lower for p in uncertainty_phrases):
        errors.append('Answer contains uncertainty phrases')

    return {'valid': len(errors) == 0, 'errors': errors}