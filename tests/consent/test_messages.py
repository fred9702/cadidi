from app.consent.messages import get_message


def test_unknown_message_is_french():
    msg = get_message("unknown", "en")
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
