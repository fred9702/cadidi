from app.consent.triggers import match_trigger


# --- Existing behavior (bare trigger words) ---

def test_consent_yes_en():
    assert match_trigger("YES") == {"trigger": "consent", "email": None}


def test_consent_oui_fr():
    assert match_trigger("oui") == {"trigger": "consent", "email": None}


def test_consent_si_es():
    assert match_trigger("SÍ") == {"trigger": "consent", "email": None}


def test_consent_si_no_accent_es():
    assert match_trigger("si") == {"trigger": "consent", "email": None}


def test_consent_sim_pt():
    assert match_trigger("Sim") == {"trigger": "consent", "email": None}


def test_opt_out_stop():
    assert match_trigger("STOP") == {"trigger": "opt_out", "email": None}


def test_opt_out_arreter_fr():
    assert match_trigger("arrêter") == {"trigger": "opt_out", "email": None}


def test_opt_out_arreter_no_accent_fr():
    assert match_trigger("ARRETER") == {"trigger": "opt_out", "email": None}


def test_opt_out_parar():
    assert match_trigger("parar") == {"trigger": "opt_out", "email": None}


def test_rejoin_en():
    assert match_trigger("join") == {"trigger": "rejoin", "email": None}


def test_rejoin_fr():
    assert match_trigger("REJOINDRE") == {"trigger": "rejoin", "email": None}


def test_rejoin_es():
    assert match_trigger("unirse") == {"trigger": "rejoin", "email": None}


def test_rejoin_pt():
    assert match_trigger("juntar") == {"trigger": "rejoin", "email": None}


def test_no_match_random_text():
    assert match_trigger("hello") == {"trigger": None, "email": None}


def test_no_match_empty_string():
    assert match_trigger("") == {"trigger": None, "email": None}


def test_match_with_whitespace():
    assert match_trigger("  yes  ") == {"trigger": "consent", "email": None}


# --- New: consent word + email ---

def test_consent_oui_with_email():
    assert match_trigger("OUI user@example.com") == {"trigger": "consent", "email": "user@example.com"}


def test_consent_yes_with_email():
    assert match_trigger("yes alice@test.org") == {"trigger": "consent", "email": "alice@test.org"}


def test_consent_sim_with_email():
    assert match_trigger("SIM bob@mail.com") == {"trigger": "consent", "email": "bob@mail.com"}


def test_consent_si_accent_with_email():
    assert match_trigger("sí carlos@test.es") == {"trigger": "consent", "email": "carlos@test.es"}


def test_consent_with_email_extra_whitespace():
    assert match_trigger("  OUI   user@example.com  ") == {"trigger": "consent", "email": "user@example.com"}


def test_opt_out_with_trailing_text_no_match():
    """Opt-out words do NOT support email suffix — must be exact."""
    assert match_trigger("STOP user@example.com") == {"trigger": None, "email": None}


def test_rejoin_with_trailing_text_no_match():
    """Rejoin words do NOT support email suffix — must be exact."""
    assert match_trigger("join user@example.com") == {"trigger": None, "email": None}


def test_consent_with_invalid_email_no_match():
    """If the second token isn't a valid email, treat as no match."""
    assert match_trigger("OUI notanemail") == {"trigger": None, "email": None}
