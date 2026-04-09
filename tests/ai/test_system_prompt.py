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


def test_system_prompt_contains_kb_content():
    prompt = get_system_prompt("fr")
    # From PROGRAMME_KB.md
    assert "Cité de la Démocratie" in prompt
    # From CAP241_KB.md
    assert "CAP 241" in prompt
    assert "EQUILIBRES" in prompt
    # From BuildingResilience_KB.md
    assert "Fondation Ma Bannière" in prompt


def test_system_prompt_contains_escalation_instructions():
    prompt = get_system_prompt("fr")
    assert "[ESCALATE]" in prompt
    assert "[REASON:" in prompt


def test_system_prompt_correct_oaflad_name():
    prompt = get_system_prompt("fr")
    assert "Premières Dames" in prompt or "First Ladies" in prompt
