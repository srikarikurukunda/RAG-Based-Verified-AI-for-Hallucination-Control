# conftest.py stubs the `groq` package before this import, so no real API
# key or network access is needed to test the pure parsing logic here.
from ai_module import parse_response


def test_parse_response_extracts_reasoning_and_answer():
    raw = (
        "REASONING:\n"
        "Step 1: Look at the context.\n"
        "Step 2: Extract the fact.\n\n"
        "FINAL ANSWER:\n"
        "The sky appears blue due to Rayleigh scattering."
    )
    result = parse_response(raw)
    assert "Step 1" in result["reasoning"]
    assert "Step 2" in result["reasoning"]
    assert result["answer"] == "The sky appears blue due to Rayleigh scattering."
    assert result["raw"] == raw


def test_parse_response_missing_markers_returns_empty_fields():
    raw = "Sorry, this response doesn't follow the expected format at all."
    result = parse_response(raw)
    assert result["reasoning"] == ""
    assert result["answer"] == ""
    assert result["raw"] == raw


def test_parse_response_missing_final_answer_marker_returns_empty_fields():
    # Only one of the two required markers is present — current
    # implementation deliberately leaves both fields empty rather than
    # guessing, so verify_response() downstream correctly flags it.
    raw = "REASONING:\nStep 1: partial only, no final answer marker."
    result = parse_response(raw)
    assert result["reasoning"] == ""
    assert result["answer"] == ""
