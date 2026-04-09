from app.escalation.detector import parse_response


def test_parse_normal_response():
    result = parse_response("Hello, how can I help you?")
    assert result["escalated"] is False
    assert result["reason"] is None
    assert result["reply"] == "Hello, how can I help you?"


def test_parse_escalated_response_with_reason():
    raw = "[ESCALATE][REASON: VIP logistics request]I've notified the team. Someone will respond shortly."
    result = parse_response(raw)
    assert result["escalated"] is True
    assert result["reason"] == "VIP logistics request"
    assert result["reply"] == "I've notified the team. Someone will respond shortly."


def test_parse_escalated_response_without_reason():
    raw = "[ESCALATE]I've notified the team."
    result = parse_response(raw)
    assert result["escalated"] is True
    assert result["reason"] is None
    assert result["reply"] == "I've notified the team."


def test_parse_escalate_marker_case_insensitive():
    raw = "[escalate][REASON: test]Reply here."
    result = parse_response(raw)
    assert result["escalated"] is True
    assert result["reason"] == "test"
    assert result["reply"] == "Reply here."


def test_parse_escalate_not_at_start():
    raw = "Some text [ESCALATE] more text"
    result = parse_response(raw)
    assert result["escalated"] is False
    assert result["reply"] == "Some text [ESCALATE] more text"
