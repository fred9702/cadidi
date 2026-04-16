from app.consent.messages import get_message


def test_unknown_message_fr():
    msg = get_message("unknown", "fr")
    assert "réservé aux participants" in msg


def test_unknown_message_en():
    msg = get_message("unknown", "en")
    assert "reserved for registered" in msg


def test_unknown_message_es():
    msg = get_message("unknown", "es")
    assert "reservado" in msg


def test_unknown_message_pt():
    msg = get_message("unknown", "pt")
    assert "reservado" in msg


def test_unknown_message_unknown_lang_falls_back_to_fr():
    msg = get_message("unknown", "xx")
    assert "réservé aux participants" in msg


def test_consent_prompt_fr():
    msg = get_message("consent_prompt", "fr")
    assert "Répondez OUI" in msg


def test_consent_prompt_en():
    msg = get_message("consent_prompt", "en")
    assert "Reply YES" in msg


def test_consent_prompt_es():
    msg = get_message("consent_prompt", "es")
    assert "Responda SÍ" in msg


def test_consent_prompt_pt():
    msg = get_message("consent_prompt", "pt")
    assert "Responda SIM" in msg


def test_opted_out_fr():
    msg = get_message("opted_out", "fr")
    assert "désabonné" in msg


def test_opted_out_en():
    msg = get_message("opted_out", "en")
    assert "unsubscribed" in msg


def test_welcome_back_fr():
    msg = get_message("welcome_back", "fr")
    assert "Bon retour" in msg


def test_welcome_back_en():
    msg = get_message("welcome_back", "en")
    assert "Welcome back" in msg


def test_unknown_language_falls_back_to_fr():
    msg = get_message("consent_prompt", "xx")
    assert "Répondez OUI" in msg


def test_welcome_menu_french():
    msg = get_message("welcome_menu", "fr")
    assert "BuildingResilience" in msg
    assert "CAP 241" in msg
    assert "Fondation Ma Bannière" in msg or "Ma Bannière" in msg


def test_welcome_menu_english():
    msg = get_message("welcome_menu", "en")
    assert "BuildingResilience" in msg
    assert "CAP 241" in msg


def test_welcome_menu_falls_back_to_french():
    msg = get_message("welcome_menu", "xx")
    assert "BuildingResilience" in msg
    assert "CAP 241" in msg


def test_escalation_holding_french():
    msg = get_message("escalation_holding", "fr")
    assert "équipe" in msg.lower() or "equipe" in msg.lower()


def test_escalation_holding_english():
    msg = get_message("escalation_holding", "en")
    assert "team" in msg.lower()
