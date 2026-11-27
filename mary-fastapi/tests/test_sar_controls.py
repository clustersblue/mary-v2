"""Article 15 disclosure rules. These tests do not build a PDF."""

import datetime

import pytest

from app.services.sar_controls import prepare_sar_disclosure, validate_sar_request


def test_reason_and_request_date_are_required():
    today = datetime.date.today()
    assert validate_sar_request("  Daughter   requested the file  ", today) == "Daughter requested the file"
    with pytest.raises(ValueError, match="reason"):
        validate_sar_request("   short  ", today)
    with pytest.raises(ValueError, match="future"):
        validate_sar_request("Daughter requested the file", today + datetime.timedelta(days=1))


def test_third_party_contacts_are_withheld_until_reviewed():
    source = {
        "full_name": "Ada Example",
        "patient": {
            "next_of_kin": "Sam Example",
            "nok_contact_number": "07000 000000",
            "nok_address": "1 High Street",
            "second_contact": "Jo Example",
            "second_contact_number": "07000 000001",
        },
        "notes": [{"carer_first": "Riley", "carer_last": "Jones", "carer_user": "rjones", "notes": "Visit"}],
        "transactions": [{"carer_first": "Riley", "carer_last": "Jones"}],
    }
    withheld = prepare_sar_disclosure(source, False, datetime.date(2026, 11, 1))
    assert withheld["patient"]["next_of_kin"] == "Sam Example"
    assert "07000" not in withheld["patient"]["nok_contact_number"]
    assert withheld["patient"]["nok_address"] != "1 High Street"
    assert withheld["notes"][0]["carer_last"] == ""
    assert withheld["notes"][0]["carer_user"] == ""
    assert withheld["notes"][0]["carer_first"] == "Riley"
    assert withheld["transactions"][0]["carer_last"] == ""
    assert source["notes"][0]["carer_last"] == "Jones"

    released = prepare_sar_disclosure(source, True, datetime.date(2026, 11, 1))
    assert released["patient"]["nok_contact_number"] == "07000 000000"
    assert released["notes"][0]["carer_last"] == "Jones"
    assert released["third_parties_included"] is True
