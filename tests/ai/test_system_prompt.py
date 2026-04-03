from app.ai.system_prompt import get_system_prompt


def test_system_prompt_contains_event_details():
    prompt = get_system_prompt("fr")
    assert "BuildingResilience" in prompt
    assert "17" in prompt
    assert "2026" in prompt
    assert "Libreville" in prompt
    assert "OAFLAD" in prompt


def test_system_prompt_french_instruction():
    prompt = get_system_prompt("fr")
    assert "français" in prompt.lower() or "french" in prompt.lower()


def test_system_prompt_english_instruction():
    prompt = get_system_prompt("en")
    assert "English" in prompt or "english" in prompt


def test_system_prompt_contains_knowledge_base_placeholder():
    prompt = get_system_prompt("fr")
    assert "KNOWLEDGE BASE" in prompt.upper() or "knowledge base" in prompt.lower()
