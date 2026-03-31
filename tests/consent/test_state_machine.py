from unittest.mock import MagicMock
from app.consent.state_machine import resolve_consent_state, process_message


def _mock_supabase(row=None):
    """Create a mock Supabase client that returns the given row."""
    sb = MagicMock()
    query = sb.table.return_value.select.return_value.eq.return_value.execute
    if row:
        query.return_value.data = [row]
    else:
        query.return_value.data = []
    return sb


def test_resolve_unknown_when_no_row():
    sb = _mock_supabase(row=None)
    state = resolve_consent_state(sb, "somehash")
    assert state is None


def test_resolve_registered():
    sb = _mock_supabase(row={"consent_status": "registered", "language_pref": "fr"})
    state = resolve_consent_state(sb, "somehash")
    assert state["consent_status"] == "registered"
    assert state["language_pref"] == "fr"


def test_resolve_active():
    sb = _mock_supabase(row={"consent_status": "active", "language_pref": "en"})
    state = resolve_consent_state(sb, "somehash")
    assert state["consent_status"] == "active"


def test_process_unknown_sender():
    sb = _mock_supabase(row=None)
    result = process_message(sb, "+447700900000", "hello")
    assert result["action"] == "reject"
    assert "réservé" in result["reply"]


def test_process_registered_with_consent_keyword():
    sb = _mock_supabase(row={"consent_status": "registered", "language_pref": "en"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "YES")
    assert result["action"] == "activate"
    sb.table.return_value.update.assert_called()


def test_process_registered_without_consent_keyword():
    sb = _mock_supabase(row={"consent_status": "registered", "language_pref": "fr"})
    result = process_message(sb, "+447700900000", "bonjour")
    assert result["action"] == "prompt_consent"
    assert "Répondez OUI" in result["reply"]


def test_process_active_normal_message():
    sb = _mock_supabase(row={"consent_status": "active", "language_pref": "en"})
    result = process_message(sb, "+447700900000", "What is the event schedule?")
    assert result["action"] == "forward_to_ai"


def test_process_active_opt_out():
    sb = _mock_supabase(row={"consent_status": "active", "language_pref": "en"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "STOP")
    assert result["action"] == "opt_out"
    assert "unsubscribed" in result["reply"]
    sb.table.return_value.update.assert_called()


def test_process_opted_out_rejoin():
    sb = _mock_supabase(row={"consent_status": "opted_out", "language_pref": "fr"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "REJOINDRE")
    assert result["action"] == "rejoin"
    assert "Bon retour" in result["reply"]
    sb.table.return_value.update.assert_called()


def test_process_opted_out_no_rejoin():
    sb = _mock_supabase(row={"consent_status": "opted_out", "language_pref": "en"})
    result = process_message(sb, "+447700900000", "hello")
    assert result["action"] == "remind_opted_out"
    assert "unsubscribed" in result["reply"]


from app.consent.hashing import hash_email


def _mock_supabase_phone_miss_email_hit(email_row):
    """Mock where phone_hash lookup returns nothing, email_hash lookup returns a row."""
    sb = MagicMock()

    # phone_hash lookup returns empty
    phone_query = MagicMock()
    phone_query.execute.return_value.data = []

    # email_hash lookup returns the row
    email_query = MagicMock()
    email_query.execute.return_value.data = [email_row]

    # update mock
    update_query = MagicMock()
    update_query.execute.return_value = None

    def select_side_effect(*args, **kwargs):
        select_mock = MagicMock()
        def eq_side_effect(col, val):
            if col == "phone_hash":
                return phone_query
            elif col == "email_hash":
                return email_query
            return MagicMock()
        select_mock.eq = eq_side_effect
        return select_mock

    def table_side_effect(name):
        mock_table = MagicMock()
        mock_table.select = select_side_effect
        mock_table.update.return_value.eq.return_value = update_query
        return mock_table

    sb.table = table_side_effect
    return sb


def test_process_unknown_phone_known_email_activates():
    sb = _mock_supabase_phone_miss_email_hit(
        {"consent_status": "registered", "language_pref": "en", "phone_hash": None}
    )
    result = process_message(sb, "+241061234567", "YES alice@example.com")
    assert result["action"] == "activate"


def test_process_unknown_phone_unknown_email_rejects():
    sb = MagicMock()
    # Both lookups return empty
    query = MagicMock()
    query.execute.return_value.data = []

    def select_side_effect(*args, **kwargs):
        select_mock = MagicMock()
        select_mock.eq.return_value = query
        return select_mock

    sb.table.return_value.select = select_side_effect
    result = process_message(sb, "+241061234567", "OUI unknown@example.com")
    assert result["action"] == "reject"


def test_process_unknown_phone_no_email_in_message_rejects():
    sb = _mock_supabase(row=None)
    result = process_message(sb, "+241061234567", "hello")
    assert result["action"] == "reject"
