"""Who may open a generated care-note PDF.

Staff and administrators can open any note. A carer can open a note only when
the file name was built from that carer's own name. A file name cannot climb
out of the storage directories.
"""

import os
import re

_SU_FILE_TOKEN = re.compile(r"^su_([^_]+)_", re.IGNORECASE)


def safe_care_note_name(filename: str) -> str | None:
    name = os.path.basename(filename or "")
    if not name or name in {".", ".."} or name != (filename or "") or ".." in name:
        return None
    return name


def carer_name_token(first_name: str, surname: str) -> str:
    return "".join(character for character in f"{first_name} {surname}".upper() if character.isalnum())


def service_user_file_token(filename: str) -> str | None:
    """The service-user number embedded in su_{number}_ files, including care notes."""
    raw = filename or ""
    name = os.path.basename(raw)
    if not name or name != raw or ".." in name:
        return None
    match = _SU_FILE_TOKEN.match(name)
    if not match:
        return None
    token = match.group(1).strip()
    if not token or token in {".", ".."}:
        return None
    return token


def carer_owns_care_note(filename: str, first_name: str, surname: str) -> bool:
    token = carer_name_token(first_name, surname)
    if not token:
        return False
    return f"_{token}_CARE_NOTE_" in (filename or "").upper()
