import re

MIN_ANSWER_LENGTH = 20
MIN_REASONING_STEPS = 2

# Exact phrase the system prompt (ai_module.py) instructs the model to use
# when the knowledge base doesn't contain the answer. This is a valid,
# intended response and must not be flagged as an uncertainty failure.
NOT_FOUND_PHRASE = 'cannot find this in the knowledge base'

# Kept narrower than before -- generic 'i cannot' matched too much benign
# text (e.g. "I cannot overstate the importance of X") in addition to
# colliding with NOT_FOUND_PHRASE above.
UNCERTAINTY_PHRASES = ['i am not sure', "i don't know", 'unclear', 'i cannot determine', 'i cannot verify']

# Matches "Step 1", "step2", "Step 3:" etc. A plain substring count of
# 'step ' was previously used here, which false-matched ordinary prose like
# "...one step here, nothing more" as a second reasoning step.
STEP_PATTERN = re.compile(r'step\s*\d+', re.IGNORECASE)


def verify_response(parsed: dict) -> dict:
    errors = []

    answer = (parsed.get('answer') or '').strip()
    reasoning = (parsed.get('reasoning') or '').strip()

    if len(answer) < MIN_ANSWER_LENGTH:
        errors.append('Answer is empty or too short')

    if len(reasoning) < 10:
        errors.append('Reasoning section is missing or too brief')

    step_count = len(set(m.lower() for m in STEP_PATTERN.findall(reasoning)))
    if step_count < MIN_REASONING_STEPS:
        errors.append(f'Expected {MIN_REASONING_STEPS} reasoning steps, found {step_count}')

    answer_lower = answer.lower()
    if NOT_FOUND_PHRASE not in answer_lower:
        if any(p in answer_lower for p in UNCERTAINTY_PHRASES):
            errors.append('Answer contains uncertainty phrases')

    return {'valid': len(errors) == 0, 'errors': errors}
