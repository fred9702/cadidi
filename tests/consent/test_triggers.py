from app.consent.triggers import match_trigger


def test_consent_yes_en():
    assert match_trigger("YES") == "consent"


def test_consent_oui_fr():
    assert match_trigger("oui") == "consent"


def test_consent_si_es():
    assert match_trigger("SÍ") == "consent"


def test_consent_si_no_accent_es():
    assert match_trigger("si") == "consent"


def test_consent_sim_pt():
    assert match_trigger("Sim") == "consent"


def test_opt_out_stop():
    assert match_trigger("STOP") == "opt_out"


def test_opt_out_arreter_fr():
    assert match_trigger("arrêter") == "opt_out"


def test_opt_out_arreter_no_accent_fr():
    assert match_trigger("ARRETER") == "opt_out"


def test_opt_out_parar():
    assert match_trigger("parar") == "opt_out"


def test_rejoin_en():
    assert match_trigger("join") == "rejoin"


def test_rejoin_fr():
    assert match_trigger("REJOINDRE") == "rejoin"


def test_rejoin_es():
    assert match_trigger("unirse") == "rejoin"


def test_rejoin_pt():
    assert match_trigger("juntar") == "rejoin"


def test_no_match_random_text():
    assert match_trigger("hello") is None


def test_no_match_empty_string():
    assert match_trigger("") is None


def test_match_with_whitespace():
    assert match_trigger("  yes  ") == "consent"
