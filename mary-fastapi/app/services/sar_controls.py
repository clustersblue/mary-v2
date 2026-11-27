"""Rules for an Article 15 copy.

The file is a disclosure to the data subject. Next-of-kin contact details and
carer surnames stay out of it until an administrator records that they were
reviewed. The reason is stored on the audit row, not printed in the file.
"""

import copy
import datetime
from typing import Any

WITHHELD = "Withheld until an administrator reviews these third-party details"
_CONTACT_FIELDS = (
    "nok_contact_number",
    "nok_address",
    "second_contact_number",
    "second_contact_address",
)


def validate_sar_request(reason: str, request_date: datetime.date) -> str:
    text = " ".join((reason or "").split())
    if len(text) < 8:
        raise ValueError("Give a short reason for this disclosure, at least 8 characters.")
    if len(text) > 500:
        raise ValueError("Reason must be 500 characters or fewer.")
    if request_date > datetime.date.today():
        raise ValueError("Request date cannot be in the future.")
    return text


def prepare_sar_disclosure(
    data: dict[str, Any],
    include_third_parties: bool,
    request_date: datetime.date,
) -> dict[str, Any]:
    prepared = copy.deepcopy(data)
    prepared["request_date"] = request_date.isoformat()
    prepared["third_parties_included"] = bool(include_third_parties)
    if include_third_parties:
        return prepared

    patient = prepared.get("patient") or {}
    for field in _CONTACT_FIELDS:
        if patient.get(field):
            patient[field] = WITHHELD
    for note in prepared.get("notes") or []:
        note["carer_last"] = ""
        note["carer_user"] = ""
    for visit in prepared.get("transactions") or []:
        visit["carer_last"] = ""
    return prepared
