"""Care-note file names and client audit fields. No PDF libraries are imported."""

import pytest

from app.services.audit import client_audit_fields, page_window
from app.services.care_note_access import carer_owns_care_note, safe_care_note_name, service_user_file_token


NOTE = "su_00001_RILEYJONES_CARE_NOTE_0900-1000_22.11.26.pdf"


def test_carer_token_matches_only_that_carer():
    assert carer_owns_care_note(NOTE, "Riley", "Jones") is True
    assert carer_owns_care_note(NOTE, "Sam", "Smith") is False
    assert carer_owns_care_note(NOTE, "Riley", "") is False


def test_service_user_token_comes_from_the_file_name():
    assert service_user_file_token(NOTE) == "00001"
    assert service_user_file_token("su_00059_careplan.pdf") == "00059"
    assert service_user_file_token("id_00012_certificate.pdf") is None
    assert service_user_file_token("../su_00001_secret.pdf") is None


def test_unsafe_care_note_names_are_rejected():
    assert safe_care_note_name(NOTE) == NOTE
    assert safe_care_note_name("../secret.pdf") is None
    assert safe_care_note_name("..") is None
    assert safe_care_note_name("folder/note.pdf") is None
    assert safe_care_note_name("") is None


def test_page_window_stays_inside_the_result_set():
    assert page_window(1, 50, 0) == (1, 0)
    assert page_window(2, 50, 120) == (2, 50)
    assert page_window(9, 50, 120) == (3, 100)


def test_client_audit_uses_known_actions_and_caps_details():
    action, record_type, details, patient = client_audit_fields(
        "view", "documents", "x" * 800, "  Ada Example  "
    )
    assert action == "VIEW"
    assert record_type == "documents"
    assert len(details) == 500
    assert patient == "Ada Example"
    with pytest.raises(ValueError):
        client_audit_fields("IMPERSONATE", "documents", "Opened a file", "Ada")
    with pytest.raises(ValueError):
        client_audit_fields("READ", "passwords", "Opened a file", "Ada")
